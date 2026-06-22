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

# A path is a test path when a *directory segment* is a test dir, or the
# *filename* follows a test convention. Segment/filename matching (not naive
# substring) avoids false positives like `latest.py` or `contest.py`.
_TEST_DIR_SEGMENTS = {"test", "tests", "spec", "specs", "__tests__", "testing"}


def is_test_path(file_path: str) -> bool:
    p = file_path.replace("\\", "/").lower()
    parts = [seg for seg in p.split("/") if seg]
    if any(seg in _TEST_DIR_SEGMENTS for seg in parts[:-1]):
        return True
    fn = parts[-1] if parts else p
    return (
        fn == "conftest.py"
        or fn.startswith("test_") or fn.startswith("test.") or fn.startswith("spec_")
        or fn.endswith("_test.py") or fn.endswith("_test.go") or fn.endswith("_spec.rb")
        or ".test." in fn or ".spec." in fn or "_spec." in fn
    )


@dataclass
class RiskedNode:
    id: int
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
                id=nid,
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


@dataclass
class Verdict:
    score: int          # 0–100 (heuristic)
    band: str           # LOW | REVIEW | HIGH
    reasons: list[str]


def verdict(radius: BlastRadius) -> Verdict:
    """A single change-risk verdict, combining the signals into one call.

    Heuristic, not a guarantee: untested hotspots and reachable public entry
    points dominate (a break there is silent and externally observable); size and
    depth add weight; existing tests that exercise the change reduce it.
    """
    from . import reach, testimpact  # lazy to avoid an import cycle

    ranked = score(radius)
    hot = sum(1 for r in ranked if r.is_hotspot)
    entries = len(reach.entry_points(radius))
    affected = len(radius.affected)
    max_depth = max((a.depth for a in radius.affected), default=0)
    tests = len(testimpact.tests_for(radius))

    s = 12 * hot + 10 * entries + min(20.0, affected * 0.4) + 3 * max_depth
    s -= min(15.0, tests * 2.0)
    s = max(0, min(100, round(s)))
    band = "LOW" if s < 30 else ("REVIEW" if s < 65 else "HIGH")

    reasons: list[str] = []
    if hot:
        reasons.append(f"{hot} untested hotspot(s)")
    if entries:
        reasons.append(f"reachable from {entries} public entry point(s)")
    reasons.append(f"{affected} definition(s) affected, depth {max_depth}")
    if tests:
        reasons.append(f"{tests} test(s) already exercise it")
    return Verdict(score=s, band=band, reasons=reasons)
