"""Exposure analysis: is a change reachable from a public entry point?

Impact analysis tells you *what* depends on a change. Exposure tells you whether
that change can be reached from the outside world — an HTTP route, a CLI command,
a public handler, a ``main`` — i.e. whether a break is *externally observable*
rather than internal-only. It's the same reachability question security triage
asks ("can an attacker actually reach this code?"), applied to change risk.

An affected definition is treated as an entry point when it is the outermost
reached node (nothing in the explored graph calls it) and/or it lives in a
route/api/cli surface. For each one we reconstruct the call path back to the
changed symbol, so a reviewer sees the exact chain from the public surface to
the change.
"""

from __future__ import annotations

from dataclasses import dataclass

from .blast_radius import BlastRadius, DefMeta
from .risk import is_test_path

ENTRY_FILE_MARKERS = (
    "route", "routes", "url", "urls", "view", "views", "endpoint", "api",
    "handler", "controller", "cli", "command", "commands", "server", "wsgi",
    "asgi", "main", "__main__",
)
ENTRY_NAME_MARKERS = (
    "main", "run", "serve", "dispatch", "handle", "handler", "index",
    "route", "endpoint",
)


@dataclass
class EntryPoint:
    meta: DefMeta
    kind: str  # route | api | cli | surface
    path: list[DefMeta]  # entry -> ... -> changed symbol


def _kind(meta: DefMeta) -> str:
    p = meta.file_path.lower()
    n = meta.name.lower()
    if any(m in p for m in ("route", "url", "view", "endpoint")) or "route" in n:
        return "route"
    if "api" in p or "handler" in p or "controller" in p:
        return "api"
    if any(m in p for m in ("cli", "command", "__main__")) or n in ("main", "run", "serve"):
        return "cli"
    return "surface"


def _is_entry(meta: DefMeta, radius: BlastRadius) -> bool:
    if is_test_path(meta.file_path):
        return False
    # structural: nothing in the explored graph calls it -> it's an outer surface
    structural = not radius.inbound.get(meta.id)
    p = meta.file_path.lower()
    n = meta.name.lower()
    semantic = any(m in p for m in ENTRY_FILE_MARKERS) or n in ENTRY_NAME_MARKERS
    return structural or semantic


def entry_points(radius: BlastRadius) -> list[EntryPoint]:
    """Affected nodes that represent public surface, with paths to the seed."""
    out: list[EntryPoint] = []
    seen: set[int] = set()
    for a in radius.affected:
        m = a.meta
        if m.id in seen or not _is_entry(m, radius):
            continue
        seen.add(m.id)
        path = [radius.defs_by_id[i] for i in radius.path_to_seed(m.id) if i in radius.defs_by_id]
        out.append(EntryPoint(meta=m, kind=_kind(m), path=path))
    order = {"route": 0, "api": 1, "cli": 2, "surface": 3}
    out.sort(key=lambda e: (order.get(e.kind, 9), len(e.path), e.meta.fqn))
    return out


def path_str(ep: EntryPoint) -> str:
    """`entry → … → changed` as a compact fqn chain."""
    names = [m.fqn or m.name for m in ep.path]
    return " → ".join(names) if names else (ep.meta.fqn or ep.meta.name)
