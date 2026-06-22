"""Test Impact Selection — which tests actually exercise this change?

The blast radius already contains every definition that transitively depends on
the change. The *test* definitions in that set are exactly the tests that
exercise it — so instead of running the whole suite, run only these. This is the
inverse of an untested hotspot, and it's the expensive feature big CI teams build
whole products around (test impact analysis / predictive test selection).
"""

from __future__ import annotations

from dataclasses import dataclass

from .blast_radius import BlastRadius
from .risk import is_test_path


@dataclass
class TestRef:
    fqn: str
    name: str
    file_path: str
    node_id: str  # pytest-style  file::name
    depth: int


def tests_for(radius: BlastRadius) -> list[TestRef]:
    """Test definitions that transitively reach the change (deduped, sorted)."""
    out: list[TestRef] = []
    seen: set[int] = set()
    for a in radius.affected:
        m = a.meta
        if m.id in seen or not is_test_path(m.file_path):
            continue
        seen.add(m.id)
        out.append(
            TestRef(
                fqn=a.fqn,
                name=m.name,
                file_path=m.file_path,
                node_id=f"{m.file_path}::{m.name}",
                depth=a.depth,
            )
        )
    out.sort(key=lambda t: (t.file_path, t.name))
    return out


def pytest_command(tests: list[TestRef]) -> str:
    """A copy-paste command that runs exactly those tests."""
    if not tests:
        return ""
    return "pytest " + " ".join(t.node_id for t in tests)
