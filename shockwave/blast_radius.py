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
    concrete definition by name (Orbit Local has no ImportedSymbol->Definition edge).
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

    @property
    def affected_files(self) -> set[str]:
        return {a.file_path for a in self.affected}


# --- SQL builders (names sourced from schema.py) -------------------------------

def _definitions_query() -> str:
    s = schema
    return (
        f"SELECT {s.DEF_ID} AS id, {s.DEF_NAME} AS name, {s.DEF_FQN} AS fqn, "
        f"{s.DEF_FILE_PATH} AS file_path, {s.DEF_TYPE} AS definition_type "
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
    via_import = (
        f"SELECT d.{s.DEF_ID} AS callee, e.{s.EDGE_SOURCE} AS caller "
        f"FROM {s.IMPORTED_SYMBOL} sym "
        f"JOIN {s.DEFINITION} d ON d.{s.DEF_NAME} = sym.{s.IMP_IDENTIFIER} "
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
        )
    return out


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

def _norm(path: str) -> str:
    return path.replace("\\", "/").lstrip("./").lower()


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
    # symbol: exact name or fqn, then fqn suffix
    exact = [d for d in defs.values() if seed in (d.name, d.fqn)]
    if exact:
        return exact
    suffix = [d for d in defs.values() if d.fqn.endswith("." + seed)]
    return suffix


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
                queue.append((caller, new_depth))

    affected = [
        AffectedNode(meta=defs[i], depth=d)
        for i, d in depth_by_id.items()
        if i in defs
    ]
    affected.sort(key=lambda a: (a.depth, a.file_path, a.fqn))
    return BlastRadius(
        seed=seed,
        seed_ids=seed_ids,
        seeds_meta=seeds_meta,
        affected=affected,
        defs_by_id=defs,
        inbound=inbound,
    )


def compute(backend: OrbitBackend, seed: str, max_hops: int = 5) -> BlastRadius:
    """Compute the transitive inbound blast radius of a symbol/file ``seed``."""
    defs = fetch_definitions(backend)
    inbound = fetch_inbound(backend)
    seeds_meta = resolve_seed(seed, defs)
    return _walk(seed, seeds_meta, defs, inbound, max_hops)


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
