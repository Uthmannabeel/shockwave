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

- **`orbit_client.py`** — `LocalBackend` shells `orbit sql`; `RemoteBackend` POSTs the JSON traversal DSL to `/api/v4/orbit/query` (anchored, one hop at a time). Local returns `list[dict]`; Remote returns nodes+edges per hop.
- **`blast_radius.py`** — resolves a seed to `gl_definition` ids, then walks **inbound** edges (`CALLS`, `EXTENDS`) in Python — a cycle-safe BFS bounded by `max_hops`. *Local:* pulls the full edge set (one `gl_edge` query) and walks it in memory; cross-file calls (`Definition --CALLS--> ImportedSymbol`) are bridged back to the concrete definition by name, disambiguated by `import_path`. *Remote:* expands one anchored traversal per hop (Remote already resolves cross-file calls to direct `Definition→Definition` edges, so it's exact, no bridge).
- **`risk.py`** — fan-in + depth + direct-test flag → score; surfaces high fan-in call sites with no direct test.
- **`stubs.py`** — generates a pytest skeleton for each not-directly-tested hotspot.
- **`ci_bot.py`** — GitLab CI bot: posts/updates the blast-radius review on a merge request (Orbit Remote).
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
