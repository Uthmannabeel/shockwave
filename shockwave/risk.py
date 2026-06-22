"""Risk scoring for blast-radius nodes.

A node's risk grows with how many things depend on it (fan-in) and how close it
is to the seed (a directly-affected node is scarier than a 4-hop-away one), and
is amplified when no test calls it directly. The headline output is the set of
high-impact definitions with no direct test that a reviewer should look at first.

Note: "no direct test" means no test file calls the definition *directly* — it
may still be exercised transitively. That's a deliberately conservative signal:
a function many things depend on but nothing tests directly is fragile.
"""

from __future__ import annotations

from dataclasses import dataclass

from .blast_radius import BlastRadius
from .schema import TEST_PATH_MARKERS


def is_test_path(file_path: str) -> bool:
    p = file_path.replace("\\", "/").lower()
    return any(marker in p for marker in TEST_PATH_MARKERS)


@dataclass
class RiskedNode:
    fqn: str
    name: str
    file_path: str
    definition_type: str
    depth: int
    fan_in: int
    covered_by_test: bool
    score: float

    @property
    def is_hotspot(self) -> bool:
        """High fan-in, non-test code that no test calls directly — review first."""
        return (not self.covered_by_test) and (not is_test_path(self.file_path)) and self.fan_in >= 2


def _covered_by_test(node_id: int, radius: BlastRadius) -> bool:
    defs = radius.defs_by_id
    meta = defs.get(node_id)
    if meta and is_test_path(meta.file_path):
        return True
    # covered if any direct caller lives in a test file
    for caller in radius.inbound.get(node_id, ()):
        cm = defs.get(caller)
        if cm and is_test_path(cm.file_path):
            return True
    return False


def score(radius: BlastRadius) -> list[RiskedNode]:
    """Rank affected nodes by risk (highest first)."""
    ranked: list[RiskedNode] = []
    for node in radius.affected:
        nid = node.meta.id
        fan_in = len(radius.inbound.get(nid, ()))
        covered = _covered_by_test(nid, radius)
        # proximity: 1.0 at depth 1, decaying with distance
        proximity = 1.0 / node.depth if node.depth else 1.0
        base = fan_in * proximity
        value = base * (1.0 if covered else 2.0)  # untested code is twice as risky
        ranked.append(
            RiskedNode(
                fqn=node.fqn,
                name=node.meta.name,
                file_path=node.file_path,
                definition_type=node.meta.definition_type,
                depth=node.depth,
                fan_in=fan_in,
                covered_by_test=covered,
                score=round(value, 3),
            )
        )
    ranked.sort(key=lambda r: (-r.score, r.depth, r.fqn))
    return ranked


def hotspots(radius: BlastRadius) -> list[RiskedNode]:
    return [r for r in score(radius) if r.is_hotspot]
