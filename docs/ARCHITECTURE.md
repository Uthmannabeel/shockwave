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
- **`blast_radius.py`** — resolves a seed to `gl_definition` ids, then a DuckDB `WITH RECURSIVE` traversal of **inbound** edges in `gl_edge` (`CALLS`, `IMPORTS`, `EXTENDS`), bounded by `max_hops`, with a depth column as a cycle guard. Cross-file calls (`Definition --CALLS--> ImportedSymbol`) are bridged back to the concrete definition **by name** (`identifier_name` ↔ `name`), since Orbit Local has no `ImportedSymbol → Definition` edge.
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
| `gl_imported_symbol` | import nodes; bridge for cross-file references (`identifier_name`, `import_path`) |
| `gl_edge` | all relationships (local, flattened): `source_id`/`target_id`/`relationship_kind` |

Inbound callers of definition `X`:
`gl_edge WHERE target_id = X AND relationship_kind = 'CALLS'`, join `source_id → gl_definition`.

> Confirmed against **Orbit Local 0.75.1** via `orbit schema`: code edges are in `gl_edge` (no `gl_code_edge` locally), `relationship_kind` is UPPERCASE, node kinds are PascalCase. All names live in `schema.py`.
