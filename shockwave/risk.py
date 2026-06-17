"""Risk scoring for blast-radius nodes.

A node's risk grows with how many things depend on it (fan-in) and how close
it is to the seed (low depth = directly affected), and is amplified when the
node is *not* covered by any test in the blast radius. The headline output is
the set of high-impact, untested call sites a reviewer should look at first.

NOTE: skeleton — implemented in the core-engine task.
"""

from __future__ import annotations

from dataclasses import dataclass

from .blast_radius import BlastRadius
from .schema import TEST_PATH_MARKERS


def is_test_path(file_path: str) -> bool:
    p = file_path.lower()
    return any(marker in p for marker in TEST_PATH_MARKERS)


@dataclass
class RiskedNode:
    fqn: str
    file_path: str
    depth: int
    fan_in: int
    covered_by_test: bool
    score: float


def score(radius: BlastRadius) -> list[RiskedNode]:
    """Rank affected nodes by risk (highest first)."""
    raise NotImplementedError
