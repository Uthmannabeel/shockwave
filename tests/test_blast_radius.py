"""Algorithm tests on a hand-built fixture graph (no Orbit needed)."""

from shockwave import blast_radius, report, risk, stubs, reach, testimpact


# Fixture: caller depends on callee.  Includes a cycle (6<->7), a test-file
# caller that "covers" the seed (5), and an untested high-fan-in node (2).
DEFS = [
    {"id": 1, "name": "process_payment", "fqn": "process_payment", "file_path": "app/payments.py", "definition_type": "function"},
    {"id": 2, "name": "checkout", "fqn": "checkout", "file_path": "app/checkout.py", "definition_type": "function"},
    {"id": 3, "name": "api_handler", "fqn": "api_handler", "file_path": "app/api.py", "definition_type": "function"},
    {"id": 4, "name": "refund", "fqn": "refund", "file_path": "app/refund.py", "definition_type": "function"},
    {"id": 5, "name": "test_payment", "fqn": "test_payment", "file_path": "tests/test_pay.py", "definition_type": "function"},
    {"id": 6, "name": "helper_a", "fqn": "helper_a", "file_path": "app/a.py", "definition_type": "function"},
    {"id": 7, "name": "helper_b", "fqn": "helper_b", "file_path": "app/b.py", "definition_type": "function"},
    {"id": 8, "name": "web", "fqn": "web", "file_path": "app/web.py", "definition_type": "function"},
]
IMPACTS = [
    (1, 2), (2, 3), (2, 8), (1, 4), (1, 5), (1, 7), (7, 6), (6, 7),
]


def _fake_sql(query, impacts, defs):
    if "UNION ALL" in query:                 # inbound impacts adjacency
        return [{"callee": c, "caller": k} for c, k in impacts]
    if "source_id IN" in query:              # outbound deps (none in fixtures)
        return []
    if "gl_definition" in query:             # definitions
        return defs
    raise AssertionError(f"unexpected query: {query}")


class FakeBackend:
    def sql(self, query: str):
        return _fake_sql(query, IMPACTS, DEFS)


def test_resolves_seed_and_affected_set():
    r = blast_radius.compute(FakeBackend(), "process_payment", max_hops=5)
    assert r.seed_ids == [1]
    assert {a.meta.id for a in r.affected} == {2, 3, 4, 5, 6, 7, 8}


def test_depths():
    r = blast_radius.compute(FakeBackend(), "process_payment", max_hops=5)
    depth = {a.meta.id: a.depth for a in r.affected}
    assert depth[2] == 1 and depth[4] == 1 and depth[7] == 1  # direct callers
    assert depth[3] == 2 and depth[8] == 2 and depth[6] == 2  # two hops away


def test_max_hops_bounds_the_walk():
    r = blast_radius.compute(FakeBackend(), "process_payment", max_hops=1)
    assert {a.meta.id for a in r.affected} == {2, 4, 5, 7}


def test_cycle_terminates():
    # 6<->7 cycle must not hang or duplicate
    r = blast_radius.compute(FakeBackend(), "process_payment", max_hops=10)
    ids = [a.meta.id for a in r.affected]
    assert len(ids) == len(set(ids))


def test_risk_flags_untested_hotspot():
    r = blast_radius.compute(FakeBackend(), "process_payment", max_hops=5)
    hot = risk.hotspots(r)
    assert [h.name for h in hot] == ["checkout"]  # fan_in 2, untested, non-test file


def test_test_file_caller_marks_covered():
    r = blast_radius.compute(FakeBackend(), "process_payment", max_hops=5)
    ranked = {x.name: x for x in risk.score(r)}
    assert ranked["test_payment"].covered_by_test is True  # it IS a test file


def test_file_seed_resolves_definitions_in_file():
    r = blast_radius.compute(FakeBackend(), "app/payments.py", max_hops=5)
    assert r.seed_ids == [1]


def test_markdown_and_json_render():
    r = blast_radius.compute(FakeBackend(), "process_payment", max_hops=5)
    md = report.to_markdown(r)
    assert "Blast radius" in md and "checkout" in md
    import json
    data = json.loads(report.to_json(r))
    assert data["summary"]["affected_definitions"] == 7


def test_stubs_for_hotspots():
    r = blast_radius.compute(FakeBackend(), "process_payment", max_hops=5)
    suggestions = stubs.suggest(r)
    assert [s.fqn for s in suggestions] == ["checkout"]
    code = suggestions[0].code
    assert "def test_checkout_impact" in code
    assert "from app.checkout import checkout" in code  # module path derived from file


def test_exposure_entry_points_and_path():
    r = blast_radius.compute(FakeBackend(), "process_payment", max_hops=5)
    eps = {e.meta.name: e for e in reach.entry_points(r)}
    # api_handler is an outer surface node in app/api.py -> an 'api' entry point
    assert "api_handler" in eps
    assert eps["api_handler"].kind == "api"
    # and we can trace the call path from it back to the changed symbol
    assert [m.fqn for m in eps["api_handler"].path] == ["api_handler", "checkout", "process_payment"]
    # helper_b is called by helper_a, so it is NOT an outer entry point
    assert "helper_b" not in eps


def test_test_impact_selection():
    r = blast_radius.compute(FakeBackend(), "process_payment", max_hops=5)
    tests = testimpact.tests_for(r)
    # the test that calls process_payment is selected; non-test callers are not
    assert "tests/test_pay.py::test_payment" in [t.node_id for t in tests]
    assert testimpact.pytest_command(tests).startswith("pytest ")


def test_verdict_bands():
    r = blast_radius.compute(FakeBackend(), "process_payment", max_hops=5)
    v = risk.verdict(r)
    assert v.band in {"LOW", "REVIEW", "HIGH"}
    assert 0 <= v.score <= 100 and v.reasons


def test_clean_path_strips_only_dot_slash_prefix():
    assert blast_radius._clean_path("./a/b.py") == "a/b.py"
    assert blast_radius._clean_path("a\\b.py") == "a/b.py"
    # must NOT strip leading characters that merely happen to be '.' or '/'
    assert blast_radius._clean_path(".config/app.py") == ".config/app.py"


def test_is_test_path_word_boundary():
    assert risk.is_test_path("tests/test_x.py")
    assert risk.is_test_path("pkg/test_utils.py")
    assert risk.is_test_path("pkg/utils_test.go")
    assert risk.is_test_path("a/conftest.py")
    # the substring trap: these are NOT tests
    assert not risk.is_test_path("app/latest.py")
    assert not risk.is_test_path("app/contest.py")
    assert not risk.is_test_path("app/attest.py")


def test_entry_detection_is_not_substring():
    from shockwave.blast_radius import DefMeta
    def meta(name, path):
        return DefMeta(id=1, name=name, fqn=name, file_path=path, definition_type="function")
    # `review.py` must NOT count as a `view` entry surface
    assert not reach._is_entry(meta("process", "app/review.py"), None)
    # genuine surfaces
    assert reach._is_entry(meta("x", "app/routes.py"), None)
    assert reach._is_entry(meta("route", "core/scaffold.py"), None)
    assert reach._is_entry(meta("handler", "svc/api/v1.py"), None)


def test_fqn_seed_does_not_conflate_same_names():
    defs = [
        {"id": 1, "name": "run", "fqn": "a.run", "file_path": "a.py", "definition_type": "function"},
        {"id": 2, "name": "run", "fqn": "b.run", "file_path": "b.py", "definition_type": "function"},
        {"id": 3, "name": "caller", "fqn": "c.caller", "file_path": "c.py", "definition_type": "function"},
    ]
    impacts = [(1, 3)]  # caller depends on a.run only

    class FB:
        def sql(self, q):
            return _fake_sql(q, impacts, defs)

    # fully-qualified seed resolves to exactly one definition (no conflation)
    r = blast_radius.compute(FB(), "a.run", max_hops=3)
    assert r.seed_ids == [1]
    # bare ambiguous name resolves to both and warns
    r2 = blast_radius.compute(FB(), "run", max_hops=3)
    assert set(r2.seed_ids) == {1, 2}
    assert any("matched" in w for w in r2.warnings)


def test_mermaid_and_html_escape_special_chars():
    defs = [{"id": 1, "name": "op<T>", "fqn": 'ns::op"x"', "file_path": "a.cpp", "definition_type": "function"},
            {"id": 2, "name": "caller|bad", "fqn": "caller|bad", "file_path": "b.cpp", "definition_type": "function"}]
    impacts = [(1, 2)]

    class FB:
        def sql(self, q):
            return _fake_sql(q, impacts, defs)

    r = blast_radius.compute(FB(), "op<T>", max_hops=3)
    merm = report.to_mermaid(r)
    assert '"op<T>"' not in merm and '["' in merm  # angle brackets were escaped
    html = report.to_html(r)
    assert "op&lt;T&gt;" in html or "op<T>" not in html  # html-escaped in the table


# ----- remote backend (iterative anchored BFS) -----

R_NODES = {
    1: {"id": 1, "name": "compute", "fqn": "pkg.compute", "file_path": "pkg/core.py", "definition_type": "function"},
    2: {"id": 2, "name": "service", "fqn": "pkg.service", "file_path": "pkg/service.py", "definition_type": "function"},
    3: {"id": 3, "name": "handler", "fqn": "pkg.handler", "file_path": "pkg/api.py", "definition_type": "function"},
    9: {"id": 9, "name": "worker_a", "fqn": "pkg.worker_a", "file_path": "pkg/worker.py", "definition_type": "function"},
    10: {"id": 10, "name": "worker_b", "fqn": "pkg.worker_b", "file_path": "pkg/worker.py", "definition_type": "function"},
}
# (caller, callee): caller depends on callee
R_EDGES = [(2, 1), (3, 2), (9, 3), (10, 3)]


class FakeRemoteBackend:
    def __init__(self, nodes, edges):
        self.nodes, self.edges = nodes, edges

    def _result(self, callee_ids):
        callee_ids = set(callee_ids)
        es = [(c, k) for (c, k) in self.edges if k in callee_ids]
        ids = set(callee_ids) | {c for c, _ in es} | {k for _, k in es}
        return {i: self.nodes[i] for i in ids if i in self.nodes}, es

    def callers_by_filter(self, filters):
        if "name" in filters:
            ids = {i for i, n in self.nodes.items() if n["name"] == filters["name"]}
        else:
            ids = {i for i, n in self.nodes.items() if n["file_path"] == filters["file_path"]}
        return self._result(ids)

    def callers_by_ids(self, ids):
        return self._result({int(i) for i in ids})

    def callees_by_ids(self, ids):
        ids = {int(i) for i in ids}
        es = [(c, k) for (c, k) in self.edges if c in ids]  # outbound: caller in ids
        nodes = {i: self.nodes[i] for c, k in es for i in (c, k) if i in self.nodes}
        return nodes, es


def test_remote_affected_and_depths():
    b = FakeRemoteBackend(R_NODES, R_EDGES)
    r = blast_radius.compute_remote(b, "compute", max_hops=5)
    assert r.seed_ids == [1]
    depth = {a.meta.id: a.depth for a in r.affected}
    assert depth == {2: 1, 3: 2, 9: 3, 10: 3}


def test_remote_fan_in_complete_at_boundary():
    # With max_hops=2, handler(3) is discovered at the last hop and never
    # expanded in the loop; the boundary pass must still complete its fan-in
    # (callers 9 and 10) without adding them as affected.
    b = FakeRemoteBackend(R_NODES, R_EDGES)
    r = blast_radius.compute_remote(b, "compute", max_hops=2)
    ids = {a.meta.id for a in r.affected}
    assert ids == {2, 3}  # 9,10 are beyond max_hops, not affected
    ranked = {x.fqn: x for x in risk.score(r)}
    assert ranked["pkg.handler"].fan_in == 2  # completed by the boundary query
    assert ranked["pkg.handler"].is_hotspot  # high fan-in, no direct test


def test_remote_file_seed():
    b = FakeRemoteBackend(R_NODES, R_EDGES)
    r = blast_radius.compute_remote(b, "pkg/core.py", max_hops=2)
    assert r.seed_ids == [1]
    assert {a.meta.id for a in r.affected} == {2, 3}
