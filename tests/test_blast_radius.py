"""Algorithm tests on a hand-built fixture graph (no Orbit needed)."""

from shockwave import blast_radius, report, risk


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


class FakeBackend:
    def sql(self, query: str):
        if "UNION ALL" in query:
            return [{"callee": c, "caller": k} for c, k in IMPACTS]
        if "gl_definition" in query:
            return DEFS
        raise AssertionError(f"unexpected query: {query}")


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
