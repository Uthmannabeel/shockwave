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

    Orbit Remote speaks a JSON DSL rather than raw SQL, so this backend is a
    thin placeholder: the Catalog agent (``catalog/agent.yaml``) is the primary
    Remote consumer. Implemented opportunistically.
    """

    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def sql(self, query: str) -> list[dict[str, Any]]:  # pragma: no cover
        raise OrbitError(
            "RemoteBackend does not accept raw SQL. Use the AI Catalog agent for "
            "Orbit Remote, or run Shockwave against Orbit Local."
        )
