# ⚡ Blast radius: `shockwave.risk.is_test_path`

**11** definitions across **4** files depend on this change.
 🔥 **3** high-impact **untested** hotspot(s) need review.

## 🔥 Untested hotspots (review first)

| Definition | File | Depth | Fan-in | Risk |
| --- | --- | --: | --: | --: |
| `shockwave.report.to_mermaid` | `shockwave/report.py` | 1 | 2 | 4.0 |
| `shockwave.risk.score` | `shockwave/risk.py` | 2 | 2 | 2.0 |
| `shockwave.report.to_dict` | `shockwave/report.py` | 3 | 2 | 1.333 |

## Affected definitions by file

### `shockwave/cli.py`

| Definition | Type | Depth | Fan-in | Tested |
| --- | --- | --: | --: | :-: |
| `_render` | Function | 2 | 1 | — |
| `main` | Function | 3 | 0 | — |

### `shockwave/report.py`

| Definition | Type | Depth | Fan-in | Tested |
| --- | --- | --: | --: | :-: |
| `to_markdown` | Function | 1 | 2 | ✅ |
| `to_mermaid` | Function | 1 | 2 | — |
| `to_html` | Function | 2 | 1 | — |
| `to_dict` | Function | 3 | 2 | — |
| `to_json` | Function | 4 | 2 | ✅ |

### `shockwave/risk.py`

| Definition | Type | Depth | Fan-in | Tested |
| --- | --- | --: | --: | :-: |
| `is_hotspot` | DecoratedMethod | 1 | 0 | — |
| `_covered_by_test` | Function | 1 | 1 | — |
| `score` | Function | 2 | 2 | — |

### `tests/test_blast_radius.py` *(tests)*

| Definition | Type | Depth | Fan-in | Tested |
| --- | --- | --: | --: | :-: |
| `test_markdown_and_json_render` | Function | 2 | 0 | ✅ |
