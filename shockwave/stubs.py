"""Suggest test stubs for the untested hotspots in a blast radius.

Shockwave doesn't just flag risk — for every high-impact definition that nothing
tests, it emits a ready-to-fill pytest skeleton so you know exactly what to
cover before shipping a change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .blast_radius import BlastRadius
from . import risk as risk_mod


def _module_path(file_path: str) -> str:
    """`pkg/sub/mod.py` -> `pkg.sub.mod` (best-effort import path)."""
    p = file_path.replace("\\", "/")
    p = re.sub(r"\.py$", "", p)
    return p.replace("/", ".")


def _test_name(node) -> str:
    leaf = node.name or (node.fqn.split(".")[-1] if node.fqn else "symbol")
    safe = re.sub(r"[^0-9a-zA-Z_]", "_", leaf)
    return f"test_{safe}_impact"


@dataclass
class Stub:
    fqn: str
    file_path: str
    code: str


def stub_for(node) -> Stub:
    mod = _module_path(node.file_path)
    leaf = node.name or node.fqn.split(".")[-1]
    test_fn = _test_name(node)
    code = (
        f"def {test_fn}():\n"
        f'    """Cover {node.fqn or leaf}.\n\n'
        f"    Flagged by Shockwave: {node.fan_in} dependents, no test coverage,\n"
        f"    depth {node.depth} in the blast radius. Changing it could break callers silently.\n"
        f'    """\n'
        f"    from {mod} import {leaf}  # noqa: import inside test for the stub\n"
        f"    # TODO: arrange inputs, call {leaf}(...), and assert the behavior\n"
        f"    # callers depend on the current contract — pin it here first.\n"
        f"    raise NotImplementedError\n"
    )
    return Stub(fqn=node.fqn or leaf, file_path=node.file_path, code=code)


def suggest(radius: BlastRadius) -> list[Stub]:
    """One pytest stub per untested hotspot, highest risk first."""
    return [stub_for(h) for h in risk_mod.hotspots(radius)]
