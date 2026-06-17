"""Backends for querying the Orbit graph.

``LocalBackend`` shells out to ``orbit sql`` (the official Orbit Local query
interface) and parses the result. ``RemoteBackend`` POSTs the JSON DSL to
``/api/v4/orbit/query`` on a GitLab instance. Both return plain ``list[dict]``
rows so the rest of Shockwave is backend-agnostic.

NOTE: skeleton — implemented in the core-engine task.
"""

from __future__ import annotations

from typing import Any, Protocol


class OrbitBackend(Protocol):
    def sql(self, query: str) -> list[dict[str, Any]]:
        """Run a query and return rows as dicts."""
        ...


class LocalBackend:
    """Query the local DuckDB graph via the ``orbit sql`` CLI."""

    def __init__(self, orbit_bin: str = "orbit") -> None:
        self.orbit_bin = orbit_bin

    def sql(self, query: str) -> list[dict[str, Any]]:
        raise NotImplementedError  # TODO: subprocess orbit sql --format json


class RemoteBackend:
    """Query Orbit Remote via POST /api/v4/orbit/query (JSON DSL)."""

    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def sql(self, query: str) -> list[dict[str, Any]]:
        raise NotImplementedError  # TODO: translate to JSON DSL traversal
