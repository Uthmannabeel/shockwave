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

# Matched as directory *segments* / filenames / name *tokens* — never raw
# substrings (so `review.py` isn't treated as a `view` surface).
_ENTRY_DIR_SEGMENTS = {
    "route", "routes", "url", "urls", "view", "views", "endpoint", "endpoints",
    "api", "apis", "handler", "handlers", "controller", "controllers",
    "cli", "command", "commands", "server",
}
# Note: deliberately excludes `app.py` — frameworks dump lots of non-entry code
# there, so it would over-report. We rely on entry *directories* and name tokens.
_ENTRY_FILENAMES = {
    "urls.py", "routes.py", "views.py", "api.py", "cli.py", "main.py",
    "server.py", "wsgi.py", "asgi.py", "manage.py", "__main__.py",
}
_ENTRY_NAME_TOKENS = {
    "main", "run", "serve", "dispatch", "handle", "handler", "index",
    "route", "endpoint",
}


@dataclass
class EntryPoint:
    meta: DefMeta
    kind: str  # route | api | cli | surface
    path: list[DefMeta]  # entry -> ... -> changed symbol


def _segments(meta: DefMeta):
    parts = [s for s in meta.file_path.replace("\\", "/").lower().split("/") if s]
    return parts[:-1], (parts[-1] if parts else "")


def _kind(meta: DefMeta) -> str:
    dirs, fn = _segments(meta)
    n = meta.name.lower()
    if any(s in ("route", "routes", "url", "urls", "view", "views", "endpoint", "endpoints") for s in dirs) \
            or fn in ("urls.py", "routes.py", "views.py") or n in ("route", "endpoint"):
        return "route"
    if any(s in ("api", "apis", "handler", "handlers", "controller", "controllers") for s in dirs) \
            or fn in ("api.py",) or n in ("handle", "handler", "dispatch"):
        return "api"
    if any(s in ("cli", "command", "commands") for s in dirs) \
            or fn in ("cli.py", "main.py", "manage.py", "__main__.py") or n in ("main", "run", "serve"):
        return "cli"
    return "surface"


def _is_entry(meta: DefMeta, radius: BlastRadius) -> bool:
    """A genuine *external* entry point: a route/API/CLI/main surface.

    We require a semantic signal — a test-free file in an entry directory, a
    recognized entry filename, or a definition whose name is an entry token.
    Matching is on path segments / filenames / name tokens, never substrings,
    and a structural root alone is not enough, so "externally observable" stays
    honest.
    """
    if is_test_path(meta.file_path):
        return False
    dirs, fn = _segments(meta)
    return (
        any(s in _ENTRY_DIR_SEGMENTS for s in dirs)
        or fn in _ENTRY_FILENAMES
        or meta.name.lower() in _ENTRY_NAME_TOKENS
    )


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
