"""Core blast-radius algorithm.

Given a seed (symbol fqn/name or file path), resolve it to one or more
``gl_definition`` ids, then compute the transitive *inbound* closure over
``gl_code_edge`` (calls + imports via the ImportedSymbol bridge + extends),
bounded by ``max_hops``. Returns affected definitions with their minimum
hop distance from the seed.

NOTE: skeleton — implemented in the core-engine task.
"""

from __future__ import annotations

from dataclasses import dataclass

from .orbit_client import OrbitBackend


@dataclass
class AffectedNode:
    definition_id: int
    fqn: str
    file_path: str
    definition_type: str
    depth: int  # minimum hops from the seed


@dataclass
class BlastRadius:
    seed: str
    seed_ids: list[int]
    affected: list[AffectedNode]


def resolve_seed(backend: OrbitBackend, seed: str) -> list[int]:
    """Resolve a symbol name/fqn or file path to gl_definition ids."""
    raise NotImplementedError


def compute(backend: OrbitBackend, seed: str, max_hops: int = 5) -> BlastRadius:
    """Compute the transitive inbound blast radius of ``seed``."""
    raise NotImplementedError
