"""Render a blast radius as Markdown, a Mermaid graph, JSON, or HTML."""

from __future__ import annotations

import json
from collections import defaultdict

from .blast_radius import BlastRadius
from . import risk as risk_mod
from . import stubs as stubs_mod


def _seed_label(radius: BlastRadius) -> str:
    # A single resolved symbol gets its fqn; otherwise show the original
    # seed string (a file path, or the changed-file list for `diff`).
    if len(radius.seeds_meta) == 1:
        m = radius.seeds_meta[0]
        return m.fqn or m.name
    return radius.seed


def to_markdown(radius: BlastRadius) -> str:
    ranked = risk_mod.score(radius)
    hotspots = [r for r in ranked if r.is_hotspot]
    files = sorted(radius.affected_files)
    lines: list[str] = []
    lines.append(f"# ⚡ Blast radius: `{_seed_label(radius)}`")
    lines.append("")
    if not radius.seed_ids:
        lines.append(f"> No definition matched `{radius.seed}` in the indexed graph.")
        return "\n".join(lines)
    lines.append(
        f"**{len(radius.affected)}** definitions across **{len(files)}** files "
        f"depend on this change."
    )
    if hotspots:
        lines.append(
            f" 🔥 **{len(hotspots)}** high-impact **untested** hotspot(s) need review."
        )
    lines.append("")

    if hotspots:
        lines.append("## 🔥 Untested hotspots (review first)")
        lines.append("")
        lines.append("| Definition | File | Depth | Fan-in | Risk |")
        lines.append("| --- | --- | --: | --: | --: |")
        for r in hotspots:
            lines.append(
                f"| `{r.fqn or r.name}` | `{r.file_path}` | {r.depth} | {r.fan_in} | {r.score} |"
            )
        lines.append("")

    if hotspots:
        lines.append("## 🧪 Suggested tests (pin the contract before you change it)")
        lines.append("")
        for stub in stubs_mod.suggest(radius):
            lines.append(f"<details><summary><code>{stub.fqn}</code></summary>")
            lines.append("")
            lines.append("```python")
            lines.append(stub.code.rstrip())
            lines.append("```")
            lines.append("</details>")
            lines.append("")

    lines.append("## Affected definitions by file")
    lines.append("")
    by_file: dict[str, list] = defaultdict(list)
    for r in ranked:
        by_file[r.file_path].append(r)
    for fp in sorted(by_file):
        tag = " *(tests)*" if risk_mod.is_test_path(fp) else ""
        lines.append(f"### `{fp}`{tag}")
        lines.append("")
        lines.append("| Definition | Type | Depth | Fan-in | Tested |")
        lines.append("| --- | --- | --: | --: | :-: |")
        for r in sorted(by_file[fp], key=lambda x: (x.depth, x.fqn)):
            tested = "✅" if r.covered_by_test else "—"
            lines.append(
                f"| `{r.name}` | {r.definition_type} | {r.depth} | {r.fan_in} | {tested} |"
            )
        lines.append("")
    return "\n".join(lines)


def to_mermaid(radius: BlastRadius) -> str:
    """A graph of seed -> affected nodes (edges follow the impact direction)."""
    def nid(i: int) -> str:
        return f"n{i}"

    lines = ["```mermaid", "graph RL"]  # right-to-left: callers point at callee
    seed_set = set(radius.seed_ids)
    for sid in radius.seed_ids:
        m = radius.defs_by_id.get(sid)
        label = (m.name if m else str(sid))
        lines.append(f'  {nid(sid)}["{label}"]:::seed')
    affected_ids = {a.meta.id for a in radius.affected}
    for a in radius.affected:
        cls = ":::hot" if not risk_mod.is_test_path(a.file_path) else ":::test"
        lines.append(f'  {nid(a.meta.id)}["{a.meta.name}"]{cls}')
    # draw inbound edges that stay within the blast set (caller -> callee)
    relevant = affected_ids | seed_set
    for callee, callers in radius.inbound.items():
        if callee not in relevant:
            continue
        for caller in callers:
            if caller in relevant:
                lines.append(f"  {nid(caller)} --> {nid(callee)}")
    lines.append("  classDef seed fill:#ff5252,stroke:#b71c1c,color:#fff;")
    lines.append("  classDef hot fill:#ffd180,stroke:#e65100;")
    lines.append("  classDef test fill:#b9f6ca,stroke:#1b5e20;")
    lines.append("```")
    return "\n".join(lines)


def to_dict(radius: BlastRadius) -> dict:
    ranked = risk_mod.score(radius)
    return {
        "seed": radius.seed,
        "resolved": [
            {"id": m.id, "fqn": m.fqn or m.name, "file_path": m.file_path}
            for m in radius.seeds_meta
        ],
        "summary": {
            "affected_definitions": len(radius.affected),
            "affected_files": len(radius.affected_files),
            "hotspots": sum(1 for r in ranked if r.is_hotspot),
        },
        "affected": [
            {
                "fqn": r.fqn or r.name,
                "name": r.name,
                "file_path": r.file_path,
                "definition_type": r.definition_type,
                "depth": r.depth,
                "fan_in": r.fan_in,
                "covered_by_test": r.covered_by_test,
                "score": r.score,
                "is_hotspot": r.is_hotspot,
            }
            for r in ranked
        ],
        "suggested_tests": [
            {"fqn": s.fqn, "file_path": s.file_path, "code": s.code}
            for s in stubs_mod.suggest(radius)
        ],
    }


def to_json(radius: BlastRadius) -> str:
    return json.dumps(to_dict(radius), indent=2)


def to_html(radius: BlastRadius) -> str:
    """Self-contained HTML: summary + the Mermaid graph rendered via CDN."""
    mermaid_body = to_mermaid(radius).removeprefix("```mermaid\n").removesuffix("\n```")
    d = to_dict(radius)
    seed = _seed_label(radius)
    rows = "\n".join(
        f"<tr class='{'hot' if a['is_hotspot'] else ''}'><td><code>{a['fqn']}</code></td>"
        f"<td><code>{a['file_path']}</code></td><td>{a['depth']}</td>"
        f"<td>{a['fan_in']}</td><td>{'✅' if a['covered_by_test'] else '—'}</td></tr>"
        for a in d["affected"]
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Shockwave — {seed}</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{startOnLoad:true}});</script>
<style>
 body{{font-family:system-ui,sans-serif;margin:2rem;background:#0d1117;color:#e6edf3}}
 h1{{color:#ff5252}} code{{color:#ffd180}}
 table{{border-collapse:collapse;width:100%;margin-top:1rem}}
 td,th{{border:1px solid #30363d;padding:.4rem .6rem;text-align:left}}
 tr.hot{{background:#3a1d00}} .summary{{font-size:1.1rem}}
 .mermaid{{background:#161b22;border-radius:8px;padding:1rem;margin:1rem 0}}
</style></head><body>
<h1>⚡ Blast radius: <code>{seed}</code></h1>
<p class="summary">{d['summary']['affected_definitions']} definitions ·
 {d['summary']['affected_files']} files ·
 🔥 {d['summary']['hotspots']} untested hotspots</p>
<div class="mermaid">{mermaid_body}</div>
<table><thead><tr><th>Definition</th><th>File</th><th>Depth</th><th>Fan-in</th><th>Tested</th></tr></thead>
<tbody>{rows}</tbody></table>
</body></html>"""
