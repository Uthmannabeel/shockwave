"""Render a blast radius as Markdown, a Mermaid graph, JSON, or HTML."""

from __future__ import annotations

import html
import json
from collections import defaultdict


def _mlabel(text: str) -> str:
    """Make a string safe to drop inside a Mermaid ``["..."]`` node label."""
    return (
        text.replace("\\", "/")
        .replace('"', "'")
        .replace("[", "(").replace("]", ")")
        .replace("{", "(").replace("}", ")")
        .replace("|", "/").replace("<", "&lt;").replace(">", "&gt;")
        .replace("`", "'")
    )

from .blast_radius import BlastRadius
from . import risk as risk_mod
from . import stubs as stubs_mod
from . import reach as reach_mod


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
    if radius.commit:
        lines.append(f"<sub>graph @ `{radius.commit[:8]}`</sub>")
    lines.append("")
    if not radius.seed_ids:
        lines.append(f"> No definition matched `{radius.seed}` in the indexed graph.")
        return "\n".join(lines)
    if len(radius.affected) == 0:
        lines.append(f"Nothing in the graph depends on `{_seed_label(radius)}` — empty blast radius. ✅")
    else:
        lines.append(
            f"**{len(radius.affected)}** definitions across **{len(files)}** files "
            f"depend on this change."
        )
    if hotspots:
        lines.append(
            f" 🔥 **{len(hotspots)}** high-impact hotspot(s) with **no direct test** need review."
        )
    entries = reach_mod.entry_points(radius)
    if entries:
        lines.append(
            f" 🚪 Reachable from **{len(entries)}** public entry point(s) — a break here is "
            f"**externally observable**."
        )
    lines.append("")
    if len(radius.seeds_meta) > 1:
        names = ", ".join(f"`{m.fqn or m.name}`" for m in radius.seeds_meta[:6])
        more = "" if len(radius.seeds_meta) <= 6 else f" (+{len(radius.seeds_meta)-6} more)"
        lines.append(f"> Resolved to {len(radius.seeds_meta)} definitions: {names}{more}")
        lines.append("")
    for w in radius.warnings:
        lines.append(f"> ⚠ {w}")
    if radius.warnings:
        lines.append("")

    if entries:
        lines.append("## 🚪 Exposure — reachable from public surface")
        lines.append("")
        lines.append("_Call paths from an external entry point down to the change._")
        lines.append("")
        lines.append("| Entry point | Kind | Path to change |")
        lines.append("| --- | --- | --- |")
        for ep in entries[:12]:
            lines.append(
                f"| `{ep.meta.fqn or ep.meta.name}` | {ep.kind} | {reach_mod.path_str(ep)} |"
            )
        lines.append("")

    if hotspots:
        lines.append("## 🔥 Hotspots with no direct test (review first)")
        lines.append("")
        lines.append("_High fan-in definitions in non-test code that no test calls directly._")
        lines.append("")
        lines.append("| Definition | File | Depth | Fan-in | Risk |")
        lines.append("| --- | --- | --: | --: | --: |")
        for r in hotspots:
            lines.append(
                f"| `{r.fqn or r.name}` | `{r.file_path}` | {r.depth} | {r.fan_in} | {r.score} |"
            )
        lines.append("")

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
        lines.append("| Definition | Type | Depth | Fan-in | Direct test |")
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
        label = _mlabel(m.name if m else str(sid))
        lines.append(f'  {nid(sid)}["{label}"]:::seed')
    affected_ids = {a.meta.id for a in radius.affected}
    for a in radius.affected:
        cls = ":::hot" if not risk_mod.is_test_path(a.file_path) else ":::test"
        lines.append(f'  {nid(a.meta.id)}["{_mlabel(a.meta.name)}"]{cls}')
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
        "commit": radius.commit,
        "warnings": list(radius.warnings),
        "resolved": [
            {"id": m.id, "fqn": m.fqn or m.name, "file_path": m.file_path}
            for m in radius.seeds_meta
        ],
        "summary": {
            "affected_definitions": len(radius.affected),
            "affected_files": len(radius.affected_files),
            "hotspots": sum(1 for r in ranked if r.is_hotspot),
            "entry_points": len(reach_mod.entry_points(radius)),
        },
        "exposure": [
            {
                "entry_point": ep.meta.fqn or ep.meta.name,
                "file_path": ep.meta.file_path,
                "kind": ep.kind,
                "path": [m.fqn or m.name for m in ep.path],
            }
            for ep in reach_mod.entry_points(radius)
        ],
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


def to_graph(radius: BlastRadius) -> dict:
    """Nodes + links for the web blast-map (ids as strings for JS safety)."""
    seed_ids = set(radius.seed_ids)
    entry_ids = {e.meta.id for e in reach_mod.entry_points(radius)}
    hot_ids = {r.id for r in risk_mod.score(radius) if r.is_hotspot}
    fan_in = {r.id: r.fan_in for r in risk_mod.score(radius)}

    depth_of = {i: 0 for i in seed_ids}
    for a in radius.affected:
        depth_of[a.meta.id] = a.depth

    def role(i: int, meta) -> str:
        if i in seed_ids:
            return "epicenter"
        if i in entry_ids:
            return "entry"
        if i in hot_ids:
            return "hotspot"
        if risk_mod.is_test_path(meta.file_path):
            return "test"
        return "normal"

    ids = list(seed_ids) + [a.meta.id for a in radius.affected]
    nodes = []
    for i in ids:
        m = radius.defs_by_id.get(i)
        if not m:
            continue
        nodes.append({
            "id": str(i),
            "label": m.name or (m.fqn.split(".")[-1] if m.fqn else str(i)),
            "fqn": m.fqn or m.name,
            "file": m.file_path,
            "depth": depth_of.get(i, 0),
            "role": role(i, m),
            "fan_in": fan_in.get(i, 0),
        })

    relevant = set(ids)
    links = []
    for callee, callers in radius.inbound.items():
        if callee not in relevant:
            continue
        for caller in callers:
            if caller in relevant:
                links.append({"source": str(caller), "target": str(callee)})

    d = to_dict(radius)
    return {
        "seed": _seed_label(radius),
        "commit": radius.commit,
        "warnings": list(radius.warnings),
        "summary": d["summary"],
        "nodes": nodes,
        "links": links,
        "exposure": d["exposure"],
        "affected": d["affected"],
        "suggested_tests": d["suggested_tests"],
    }


def to_html(radius: BlastRadius) -> str:
    """Self-contained HTML: summary + the Mermaid graph rendered via CDN."""
    mermaid_body = to_mermaid(radius).removeprefix("```mermaid\n").removesuffix("\n```")
    d = to_dict(radius)
    seed = _seed_label(radius)
    rows = "\n".join(
        f"<tr class='{'hot' if a['is_hotspot'] else ''}'><td><code>{html.escape(a['fqn'])}</code></td>"
        f"<td><code>{html.escape(a['file_path'])}</code></td><td>{a['depth']}</td>"
        f"<td>{a['fan_in']}</td><td>{'✅' if a['covered_by_test'] else '—'}</td></tr>"
        for a in d["affected"]
    )
    seed = html.escape(seed)
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
