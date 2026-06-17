# Shockwave skill (local recipe bundle)

Query recipes for computing a blast radius from the GitLab Orbit graph, for use
by AI coding agents (Claude Code, `glab`) against **Orbit Local**. Mirrors the
logic of the AI Catalog agent. (Bonus artifact — the Catalog submission is the
agent/flow under `catalog/`.)

## Recipes
See `recipes/` for ready-to-run DuckDB SQL:
- `resolve_seed.sql` — symbol/file → `gl_definition` ids
- `direct_callers.sql` — one-hop inbound callers
- `transitive_radius.sql` — `WITH RECURSIVE` transitive inbound closure
- `untested_hotspots.sql` — affected non-test call sites ranked by fan-in

> Recipes are authored alongside the engine queries so both stay in sync.
