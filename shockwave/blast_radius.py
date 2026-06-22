"""Core blast-radius algorithm.

Given a seed (symbol name/fqn or file path), resolve it to one or more
``gl_definition`` ids, then compute the transitive *inbound* impact closure:
everything that (transitively) depends on the seed and would therefore be
affected if it changed.

We pull two cheap result sets from Orbit and do the graph walk in Python — it
is cycle-safe, easy to unit-test with a fake backend, and fast at repo scale.

Impact edges (``caller`` depends on ``callee``) come from:
  * ``Definition --CALLS/EXTENDS--> Definition`` (same-graph), and
  * cross-file calls ``Definition --CALLS--> ImportedSymbol`` bridged back to the
    concrete definition by name (Orbit Local has no ImportedSymbol->Definition
    edge), disambiguated by ``import_path`` so same-named symbols in different
    modules don't collide. (Orbit *Remote* resolves these to direct edges, so
    ``compute_remote`` needs no bridge and is exact.)
"""

from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass, field

from . import schema
from .orbit_client import OrbitBackend


@dataclass(frozen=True)
class DefMeta:
    id: int
    name: str
    fqn: str
    file_path: str
    definition_type: str
    commit_sha: str = ""  # which indexed revision this came from (transparency)


@dataclass
class AffectedNode:
    meta: DefMeta
    depth: int  # minimum hops from the seed

    # convenience passthroughs
    @property
    def fqn(self) -> str:
        return self.meta.fqn or self.meta.name

    @property
    def file_path(self) -> str:
        return self.meta.file_path


@dataclass
class BlastRadius:
    seed: str
    seed_ids: list[int]
    seeds_meta: list[DefMeta]
    affected: list[AffectedNode]
    # graph context used by risk scoring / reporting
    defs_by_id: dict[int, DefMeta] = field(default_factory=dict)
    inbound: dict[int, set[int]] = field(default_factory=dict)  # callee -> {callers}
    # parents[caller] = the node it was first discovered from on the path toward
    # the seed (i.e. caller depends on parents[caller]). Lets us reconstruct a
    # call path from any affected node back to a seed.
    parents: dict[int, int] = field(default_factory=dict)
    # caveats worth showing the user (partial results, permission scoping, …)
    warnings: list[str] = field(default_factory=list)
    # direct outbound dependencies of the seed — what the change relies on
    dependencies: list[DefMeta] = field(default_factory=list)

    @property
    def commit(self) -> str:
        return self.seeds_meta[0].commit_sha if self.seeds_meta else ""

    @property
    def affected_files(self) -> set[str]:
        return {a.file_path for a in self.affected}

    def path_to_seed(self, node_id: int) -> list[int]:
        """Call path from ``node_id`` down to a seed (inclusive of both)."""
        path = [node_id]
        seen = {node_id}
        while node_id in self.parents:
            node_id = self.parents[node_id]
            if node_id in seen:
                break
            path.append(node_id)
            seen.add(node_id)
        return path


# --- SQL builders (names sourced from schema.py) -------------------------------

def _definitions_query() -> str:
    s = schema
    return (
        f"SELECT {s.DEF_ID} AS id, {s.DEF_NAME} AS name, {s.DEF_FQN} AS fqn, "
        f"{s.DEF_FILE_PATH} AS file_path, {s.DEF_TYPE} AS definition_type, "
        f"{s.DEF_COMMIT} AS commit_sha "
        f"FROM {s.DEFINITION}"
    )


def _impacts_query() -> str:
    """Rows of (callee, caller): caller depends on callee."""
    s = schema
    direct = (
        f"SELECT e.{s.EDGE_TARGET} AS callee, e.{s.EDGE_SOURCE} AS caller "
        f"FROM {s.EDGE} e "
        f"WHERE e.{s.EDGE_KIND} IN ('{s.CALLS}','{s.EXTENDS}') "
        f"AND e.{s.EDGE_SOURCE_KIND} = '{s.KIND_DEFINITION}' "
        f"AND e.{s.EDGE_TARGET_KIND} = '{s.KIND_DEFINITION}'"
    )
    # Cross-file calls appear as Definition --CALLS--> ImportedSymbol; Orbit Local
    # has no ImportedSymbol->Definition edge, so we bridge by name. To avoid
    # collisions between same-named definitions in different modules (e.g. many
    # `get`/`__init__`), we additionally require the import_path to be consistent
    # with the callee's module: either the dotted file path contains the
    # import_path, or the import_path mentions the callee's file basename. When
    # import_path is absent we fall back to the (looser) name match.
    basename = "regexp_replace(d.file_path, '(^.*/)|(\\.[^.]+$)', '', 'g')"
    dotted = "replace(d.file_path, '/', '.')"
    via_import = (
        f"SELECT d.{s.DEF_ID} AS callee, e.{s.EDGE_SOURCE} AS caller "
        f"FROM {s.IMPORTED_SYMBOL} sym "
        f"JOIN {s.DEFINITION} d ON d.{s.DEF_NAME} = sym.{s.IMP_IDENTIFIER} "
        f"AND (sym.{s.IMP_PATH} IS NULL OR sym.{s.IMP_PATH} = '' "
        f"OR {dotted} LIKE '%' || sym.{s.IMP_PATH} || '%' "
        f"OR sym.{s.IMP_PATH} LIKE '%' || {basename} || '%') "
        f"JOIN {s.EDGE} e ON e.{s.EDGE_TARGET} = sym.{s.DEF_ID} "
        f"WHERE e.{s.EDGE_KIND} = '{s.CALLS}' "
        f"AND e.{s.EDGE_TARGET_KIND} = '{s.KIND_IMPORTED_SYMBOL}' "
        f"AND e.{s.EDGE_SOURCE_KIND} = '{s.KIND_DEFINITION}'"
    )
    return f"{direct} UNION ALL {via_import}"


# --- graph loading -------------------------------------------------------------

def fetch_definitions(backend: OrbitBackend) -> dict[int, DefMeta]:
    rows = backend.sql(_definitions_query())
    out: dict[int, DefMeta] = {}
    for r in rows:
        out[int(r["id"])] = DefMeta(
            id=int(r["id"]),
            name=r.get("name") or "",
            fqn=r.get("fqn") or "",
            file_path=r.get("file_path") or "",
            definition_type=r.get("definition_type") or "",
            commit_sha=r.get("commit_sha") or "",
        )
    return out


def _outbound_query_local(seed_ids: set[int]) -> str:
    """Direct callees (outbound deps) of the seed ids: Def->Def + import bridge."""
    s = schema
    ids = ",".join(str(int(i)) for i in seed_ids)
    basename = "regexp_replace(d.file_path, '(^.*/)|(\\.[^.]+$)', '', 'g')"
    dotted = "replace(d.file_path, '/', '.')"
    direct = (
        f"SELECT e.{s.EDGE_TARGET} AS callee FROM {s.EDGE} e "
        f"WHERE e.{s.EDGE_SOURCE} IN ({ids}) "
        f"AND e.{s.EDGE_KIND} IN ('{s.CALLS}','{s.EXTENDS}') "
        f"AND e.{s.EDGE_SOURCE_KIND} = '{s.KIND_DEFINITION}' "
        f"AND e.{s.EDGE_TARGET_KIND} = '{s.KIND_DEFINITION}'"
    )
    via = (
        f"SELECT d.{s.DEF_ID} AS callee FROM {s.EDGE} e "
        f"JOIN {s.IMPORTED_SYMBOL} sym ON sym.{s.DEF_ID} = e.{s.EDGE_TARGET} "
        f"JOIN {s.DEFINITION} d ON d.{s.DEF_NAME} = sym.{s.IMP_IDENTIFIER} "
        f"AND (sym.{s.IMP_PATH} IS NULL OR sym.{s.IMP_PATH} = '' "
        f"OR {dotted} LIKE '%' || sym.{s.IMP_PATH} || '%' "
        f"OR sym.{s.IMP_PATH} LIKE '%' || {basename} || '%') "
        f"WHERE e.{s.EDGE_SOURCE} IN ({ids}) AND e.{s.EDGE_KIND} = '{s.CALLS}' "
        f"AND e.{s.EDGE_SOURCE_KIND} = '{s.KIND_DEFINITION}' "
        f"AND e.{s.EDGE_TARGET_KIND} = '{s.KIND_IMPORTED_SYMBOL}'"
    )
    return f"{direct} UNION {via}"


def direct_dependencies_local(backend, seed_ids, defs: dict[int, DefMeta]) -> list[DefMeta]:
    if not seed_ids:
        return []
    seed_set = set(seed_ids)
    out: dict[int, DefMeta] = {}
    for r in backend.sql(_outbound_query_local(seed_set)):
        cid = int(r["callee"])
        if cid in seed_set or cid not in defs:
            continue
        out[cid] = defs[cid]
    return sorted(out.values(), key=lambda m: (m.file_path, m.fqn or m.name))


def direct_dependencies_remote(backend, seed_ids, defs: dict[int, DefMeta]) -> list[DefMeta]:
    if not seed_ids:
        return []
    seed_set = set(seed_ids)
    nodes, edges = backend.callees_by_ids(list(seed_set))
    for nid, nd in nodes.items():
        defs.setdefault(nid, _meta_from_remote(nd))
    callee_ids = {callee for caller, callee in edges if callee not in seed_set}
    return sorted(
        (defs[i] for i in callee_ids if i in defs),
        key=lambda m: (m.file_path, m.fqn or m.name),
    )


def fetch_inbound(backend: OrbitBackend) -> dict[int, set[int]]:
    """Map callee_id -> set of caller_ids (who depends on callee)."""
    inbound: dict[int, set[int]] = {}
    for r in backend.sql(_impacts_query()):
        callee, caller = int(r["callee"]), int(r["caller"])
        if callee == caller:
            continue
        inbound.setdefault(callee, set()).add(caller)
    return inbound


# --- seed resolution -----------------------------------------------------------

def _clean_path(path: str) -> str:
    """Forward slashes; strip leading ``./`` segments (not arbitrary chars)."""
    p = path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def _norm(path: str) -> str:
    return _clean_path(path).lower()


def resolve_seed(seed: str, defs: dict[int, DefMeta]) -> list[DefMeta]:
    """Resolve a symbol name/fqn or file path to definitions."""
    looks_like_path = ("/" in seed) or ("\\" in seed) or os.path.splitext(seed)[1] != ""
    if looks_like_path:
        target = _norm(seed)
        hits = [
            d for d in defs.values()
            if _norm(d.file_path) == target or _norm(d.file_path).endswith("/" + target)
        ]
        if hits:
            return hits
    # Prefer the most specific match so a fully-qualified seed never conflates
    # same-named symbols: exact fqn  >  fqn suffix  >  bare name.
    fqn_exact = [d for d in defs.values() if d.fqn == seed]
    if fqn_exact:
        return fqn_exact
    if "." in seed:
        fqn_suffix = [d for d in defs.values() if d.fqn.endswith("." + seed)]
        if fqn_suffix:
            return fqn_suffix
    return [d for d in defs.values() if d.name == seed]


# --- the walk ------------------------------------------------------------------

def _walk(
    seed: str,
    seeds_meta: list[DefMeta],
    defs: dict[int, DefMeta],
    inbound: dict[int, set[int]],
    max_hops: int,
) -> BlastRadius:
    seed_ids = [d.id for d in seeds_meta]
    depth_by_id: dict[int, int] = {}
    parents: dict[int, int] = {}
    seed_set = set(seed_ids)
    queue: deque[tuple[int, int]] = deque((sid, 0) for sid in seed_ids)
    visited: set[int] = set(seed_ids)

    while queue:
        node, depth = queue.popleft()
        if depth >= max_hops:
            continue
        for caller in inbound.get(node, ()):  # who depends on `node`
            if caller in seed_set:
                continue
            new_depth = depth + 1
            prev = depth_by_id.get(caller)
            if prev is None or new_depth < prev:
                depth_by_id[caller] = new_depth
            if caller not in visited:
                visited.add(caller)
                parents[caller] = node
                queue.append((caller, new_depth))

    affected = [
        AffectedNode(meta=defs[i], depth=d)
        for i, d in depth_by_id.items()
        if i in defs
    ]
    affected.sort(key=lambda a: (a.depth, a.file_path, a.fqn))
    warnings: list[str] = []
    looks_like_path = ("/" in seed) or ("\\" in seed) or os.path.splitext(seed)[1] != ""
    if not looks_like_path and len(seeds_meta) > 1:
        files = sorted({m.file_path for m in seeds_meta})
        warnings.append(
            f"'{seed}' matched {len(seeds_meta)} definitions across {len(files)} "
            f"files; the radius is their union. Pass a fully-qualified name to disambiguate."
        )
    return BlastRadius(
        seed=seed,
        seed_ids=seed_ids,
        seeds_meta=seeds_meta,
        affected=affected,
        defs_by_id=defs,
        inbound=inbound,
        parents=parents,
        warnings=warnings,
    )


def compute(backend: OrbitBackend, seed: str, max_hops: int = 5) -> BlastRadius:
    """Compute the transitive inbound blast radius of a symbol/file ``seed``."""
    defs = fetch_definitions(backend)
    inbound = fetch_inbound(backend)
    seeds_meta = resolve_seed(seed, defs)
    radius = _walk(seed, seeds_meta, defs, inbound, max_hops)
    radius.dependencies = direct_dependencies_local(backend, radius.seed_ids, defs)
    return radius


REMOTE_HOP_LIMIT = 2000  # heuristic: a hop this big may be capped by Orbit


def _meta_from_remote(node: dict) -> DefMeta:
    return DefMeta(
        id=int(node["id"]),
        name=node.get("name") or "",
        fqn=node.get("fqn") or "",
        file_path=node.get("file_path") or "",
        definition_type=node.get("definition_type") or "",
        commit_sha=node.get("commit_sha") or "",
    )


def _seed_matches(meta: DefMeta, seed: str) -> bool:
    if "." in seed:
        return meta.fqn == seed or meta.fqn.endswith("." + seed) or meta.name == seed
    return meta.name == seed


def compute_remote(backend, seed: str, max_hops: int = 5) -> BlastRadius:
    """Blast radius against Orbit Remote via iterative anchored traversal.

    Remote forbids full-graph scans, so we expand one hop at a time: resolve the
    seed (+ its direct callers) with a property filter, then walk outward by
    ``node_ids``. Remote already resolves cross-file calls to direct
    Definition->Definition edges, so CALLS + EXTENDS is the whole story.
    """
    looks_like_path = ("/" in seed) or ("\\" in seed) or os.path.splitext(seed)[1] != ""
    if looks_like_path:
        # Orbit stores file_path with original case and forward slashes.
        anchor = {"file_path": _clean_path(seed)}
    else:
        anchor = {"name": seed.split(".")[-1]}

    defs: dict[int, DefMeta] = {}
    inbound: dict[int, set[int]] = {}
    warnings: list[str] = [
        "Remote results reflect only code your token can see — Orbit is permission-aware."
    ]
    flags = {"truncated": False}

    def ingest(nodes: dict[int, dict], edges: list[tuple[int, int]]):
        for nid, nd in nodes.items():
            defs.setdefault(nid, _meta_from_remote(nd))
        if len(edges) >= REMOTE_HOP_LIMIT:
            flags["truncated"] = True
        for caller, callee in edges:
            inbound.setdefault(callee, set()).add(caller)

    # hop 1: resolve the seed and its direct callers in one anchored query
    nodes, edges = backend.callers_by_filter(anchor)
    ingest(nodes, edges)
    if looks_like_path:
        seed_ids = {callee for _, callee in edges}
    else:
        seed_ids = {callee for _, callee in edges if callee in defs and _seed_matches(defs[callee], seed)}

    depth: dict[int, int] = {}
    parents: dict[int, int] = {}
    visited = set(seed_ids)
    frontier: set[int] = set()
    for caller, callee in edges:
        if callee in seed_ids and caller not in visited:
            depth[caller] = 1
            parents[caller] = callee
            visited.add(caller)
            frontier.add(caller)

    d = 1
    while frontier and d < max_hops:
        nodes, edges = backend.callers_by_ids(list(frontier))
        ingest(nodes, edges)
        nxt: set[int] = set()
        for caller, callee in edges:
            if caller in visited or caller in seed_ids:
                continue
            depth[caller] = d + 1
            parents[caller] = callee
            visited.add(caller)
            nxt.add(caller)
        frontier = nxt
        d += 1

    # Boundary nodes discovered at the last hop were never expanded, so their
    # inbound (used for fan-in / hotspot detection) is empty. One extra anchored
    # query over all affected ids completes the fan-in counts accurately.
    if depth:
        nodes, edges = backend.callers_by_ids(list(depth.keys()))
        ingest(nodes, edges)

    if flags["truncated"]:
        warnings.append(
            "A hop returned a very large number of callers — results may be "
            "truncated by Orbit's row limits; treat counts as a lower bound."
        )
    if not looks_like_path and len(seed_ids) > 1:
        warnings.append(
            f"'{seed}' matched {len(seed_ids)} definitions; the radius is their "
            f"union. Pass a fully-qualified name to disambiguate."
        )
    affected = [AffectedNode(meta=defs[i], depth=dep) for i, dep in depth.items() if i in defs]
    affected.sort(key=lambda a: (a.depth, a.file_path, a.fqn))
    dependencies = direct_dependencies_remote(backend, seed_ids, defs)
    return BlastRadius(
        seed=seed,
        seed_ids=sorted(seed_ids),
        seeds_meta=[defs[i] for i in seed_ids if i in defs],
        affected=affected,
        defs_by_id=defs,
        inbound=inbound,
        parents=parents,
        warnings=warnings,
        dependencies=dependencies,
    )


def compute_for_files_remote(backend, files: list[str], max_hops: int = 5) -> BlastRadius:
    """Remote blast radius of changing anything in ``files`` (merged)."""
    defs: dict[int, DefMeta] = {}
    inbound: dict[int, set[int]] = {}
    depth: dict[int, int] = {}
    parents: dict[int, int] = {}
    seed_ids: set[int] = set()
    for f in files:
        br = compute_remote(backend, f, max_hops=max_hops)
        defs.update(br.defs_by_id)
        for callee, callers in br.inbound.items():
            inbound.setdefault(callee, set()).update(callers)
        for k, v in br.parents.items():
            parents.setdefault(k, v)
        seed_ids.update(br.seed_ids)
        for a in br.affected:
            if a.meta.id not in depth or a.depth < depth[a.meta.id]:
                depth[a.meta.id] = a.depth
    affected = [
        AffectedNode(meta=defs[i], depth=d)
        for i, d in depth.items()
        if i in defs and i not in seed_ids
    ]
    affected.sort(key=lambda a: (a.depth, a.file_path, a.fqn))
    return BlastRadius(
        seed=", ".join(files),
        seed_ids=sorted(seed_ids),
        seeds_meta=[defs[i] for i in seed_ids if i in defs],
        affected=affected,
        defs_by_id=defs,
        inbound=inbound,
        parents=parents,
    )


def compute_for_files(
    backend: OrbitBackend, files: list[str], max_hops: int = 5
) -> BlastRadius:
    """Blast radius of changing anything in ``files`` (e.g. a git diff)."""
    defs = fetch_definitions(backend)
    inbound = fetch_inbound(backend)
    targets = {_norm(f) for f in files}
    seeds_meta = [
        d for d in defs.values()
        if _norm(d.file_path) in targets
        or any(_norm(d.file_path).endswith("/" + t) for t in targets)
    ]
    label = ", ".join(sorted(files))
    return _walk(label, seeds_meta, defs, inbound, max_hops)
