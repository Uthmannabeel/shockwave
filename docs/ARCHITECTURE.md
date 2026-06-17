# Architecture

Shockwave has two layers that share one blast-radius algorithm.

## 1. Core engine (`shockwave/`, Python)

Runs against **Orbit Local** and is the rigorous reference implementation.

```
cli.py ──▶ blast_radius.compute() ──▶ orbit_client (Local | Remote)
                    │                         │
                    ▼                         ▼
              risk.score()              Orbit graph (DuckDB / Remote)
                    │
                    ▼
        report.to_markdown / to_mermaid / to_html / to_json
```

- **`orbit_client.py`** — `LocalBackend` shells `orbit sql`; `RemoteBackend` POSTs the JSON DSL to `/api/v4/orbit/query`. Both return `list[dict]`.
- **`blast_radius.py`** — resolves a seed to `gl_definition` ids, then a DuckDB `WITH RECURSIVE` traversal of **inbound** edges in `gl_code_edge` (`calls`, `imports` via the `ImportedSymbol` two-hop bridge, `extends`), bounded by `max_hops`, with a depth column as a cycle guard.
- **`risk.py`** — fan-in + depth + test-coverage → score; surfaces high-impact untested call sites.
- **`report.py`** — Markdown / Mermaid / HTML / JSON renderers.
- **`schema.py`** — single source of truth for all table/column/edge-kind names (so a schema change is a one-file edit).

## 2. AI Catalog artifact (`catalog/`)

The *published* hackathon submission. A GitLab Duo **agent** (and stretch **flow**) that uses Orbit Remote's `query_graph` / `get_graph_schema` MCP tools to answer blast-radius questions and (flow) auto-comment on merge requests.

## Graph model (Orbit)

| table | role |
| --- | --- |
| `gl_definition` | functions/classes/etc. (`id`, `fqn`, `definition_type`, `file_path`, lines) |
| `gl_file` / `gl_directory` | filesystem nodes |
| `gl_imported_symbol` | import nodes; bridge for cross-file references |
| `gl_code_edge` | code relationships: `source_id`/`target_id`/`relationship_kind` |

Inbound callers of definition `X`:
`gl_code_edge WHERE target_id = X AND relationship_kind = 'calls'`, join `source_id → gl_definition`.

> Local schema specifics (table name, edge-kind casing) are confirmed via `orbit schema` and encoded in `schema.py`.
