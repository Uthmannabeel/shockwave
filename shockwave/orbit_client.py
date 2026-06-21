"""Backends for querying the Orbit graph.

``LocalBackend`` shells out to ``orbit sql --format json`` (the official Orbit
Local query interface) and parses the result. ``RemoteBackend`` POSTs the JSON
DSL to ``/api/v4/orbit/query`` on a GitLab instance. Both return plain
``list[dict]`` rows so the rest of Shockwave is backend-agnostic.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any, Protocol


class OrbitError(RuntimeError):
    """Raised when an Orbit query cannot be run or returns an error."""


def enable_os_trust() -> None:
    """Make urllib3/requests use the OS trust store.

    On networks that intercept TLS (corporate proxies), Python's bundled CA set
    won't trust the proxy's cert. truststore fixes that. No-op if unavailable or
    on networks that don't need it.
    """
    try:
        import truststore

        truststore.inject_into_ssl()
    except Exception:  # pragma: no cover - best effort
        pass


class OrbitBackend(Protocol):
    def sql(self, query: str) -> list[dict[str, Any]]:
        """Run a query and return rows as a list of dicts."""
        ...


def _find_orbit_binary() -> str:
    """Locate the ``orbit`` CLI on PATH, falling back to the default install dir."""
    found = shutil.which("orbit")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidate = os.path.join(local, "Programs", "orbit", "orbit.exe")
        if os.path.isfile(candidate):
            return candidate
    raise OrbitError(
        "Could not find the 'orbit' CLI. Install Orbit Local and ensure it is on "
        "PATH, or pass --orbit-bin."
    )


class LocalBackend:
    """Query the local DuckDB graph via the ``orbit sql`` CLI."""

    def __init__(self, orbit_bin: str | None = None, db: str | None = None) -> None:
        self.orbit_bin = orbit_bin or _find_orbit_binary()
        self.db = db

    def sql(self, query: str) -> list[dict[str, Any]]:
        cmd = [self.orbit_bin, "sql", query, "--format", "json"]
        if self.db:
            cmd += ["--db", self.db]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", check=False
            )
        except OSError as exc:  # pragma: no cover - environment dependent
            raise OrbitError(f"Failed to run orbit: {exc}") from exc
        if proc.returncode != 0:
            raise OrbitError(
                f"orbit sql failed (exit {proc.returncode}):\n{proc.stderr.strip()}"
            )
        out = proc.stdout.strip()
        if not out:
            return []
        try:
            data = json.loads(out)
        except json.JSONDecodeError as exc:
            raise OrbitError(f"Could not parse orbit output as JSON: {exc}") from exc
        return data if isinstance(data, list) else [data]


class RemoteBackend:
    """Query Orbit Remote via POST /api/v4/orbit/query (JSON DSL).

    Orbit Remote speaks a JSON traversal DSL (not raw SQL) and **forbids
    full-graph scans** — every query must be anchored by ``filters`` or
    ``node_ids``. It also resolves cross-file calls into direct
    ``Definition --CALLS--> Definition`` edges (no ImportedSymbol bridge needed).
    So the blast radius is computed by *iterative* BFS: one anchored query per
    hop (see ``blast_radius.compute_remote``).

    This backend exposes ``callers`` — given a set of definitions (by id or by a
    property filter), return who CALLS/EXTENDS them, with node metadata.
    """

    # edges that mean "the source depends on the target"
    INBOUND_EDGE_TYPES = ("CALLS", "EXTENDS")

    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _query(self, query: dict[str, Any]) -> dict[str, Any]:
        import requests

        enable_os_trust()

        url = f"{self.base_url}/api/v4/orbit/query"
        try:
            resp = requests.post(
                url,
                headers={
                    "PRIVATE-TOKEN": self.token,
                    "User-Agent": "Shockwave-BlastRadius/0.1",
                    "Accept": "application/json",
                },
                json={"query": query, "response_format": "raw"},
                timeout=60,
            )
        except requests.RequestException as exc:  # pragma: no cover - network
            raise OrbitError(f"Orbit Remote request failed: {exc}") from exc
        if resp.status_code != 200:
            raise OrbitError(
                f"Orbit query failed (HTTP {resp.status_code}): {resp.text}"
            )
        return resp.json().get("result", {})

    def _callers(self, callee_anchor: dict[str, Any]) -> tuple[dict[int, dict], list[tuple[int, int]]]:
        """Return (nodes_by_id, edges) where each edge is (caller_id, callee_id).

        ``callee_anchor`` anchors the callee node, e.g. ``{"node_ids": [..]}`` or
        ``{"filters": {"name": "compute"}}``. Runs once per inbound edge type.
        """
        nodes: dict[int, dict] = {}
        edges: list[tuple[int, int]] = []
        for edge_type in self.INBOUND_EDGE_TYPES:
            query = {
                "query_type": "traversal",
                "nodes": [
                    {"id": "callee", "entity": "Definition", **callee_anchor},
                    {"id": "caller", "entity": "Definition"},
                ],
                "relationships": [{"type": edge_type, "from": "caller", "to": "callee"}],
            }
            try:
                result = self._query(query)
            except OrbitError:
                # an edge type with no instances can 400; treat as empty
                continue
            for node in result.get("nodes", []):
                nid = int(node["id"])
                nodes[nid] = node
            for edge in result.get("edges", []):
                edges.append((int(edge["from_id"]), int(edge["to_id"])))
        return nodes, edges

    def callers_by_filter(self, filters: dict[str, Any]):
        return self._callers({"filters": filters})

    def callers_by_ids(self, node_ids: list[int]):
        return self._callers({"node_ids": [int(i) for i in node_ids]})

    def sql(self, query: str) -> list[dict[str, Any]]:  # pragma: no cover
        raise OrbitError(
            "RemoteBackend speaks the JSON DSL, not SQL. Blast radius on Orbit "
            "Remote is computed via iterative traversal (see compute_remote)."
        )
