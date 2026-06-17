"""Render a blast radius as Markdown, a Mermaid graph, or self-contained HTML.

NOTE: skeleton — implemented in the reports/UX task.
"""

from __future__ import annotations

from .blast_radius import BlastRadius


def to_markdown(radius: BlastRadius) -> str:
    """Ranked report grouped by file, with an untested-hotspot section."""
    raise NotImplementedError


def to_mermaid(radius: BlastRadius) -> str:
    """Mermaid graph of the seed and its affected nodes."""
    raise NotImplementedError


def to_html(radius: BlastRadius) -> str:
    """Self-contained interactive (D3) view."""
    raise NotImplementedError


def to_json(radius: BlastRadius) -> str:
    """Machine-readable output for CI / the catalog agent."""
    raise NotImplementedError
