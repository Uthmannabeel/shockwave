# Shockwave ⚡

**See the blast radius of a code change before it merges.**

Shockwave is a blast-radius impact-analysis tool built on the [GitLab Orbit](https://about.gitlab.com/gitlab-orbit/) knowledge graph. Point it at a changed function, file, or git diff and it traverses Orbit's resolved code graph — calls, imports, and inheritance — to show you *everything* a change can ripple into: every caller, the tests that should re-run, and the highest-risk call sites **that no test touches directly**, ranked.

> Built for the **GitLab Transcend Hackathon** (Showcase track).
>
> 🟢 **Live in the GitLab AI Catalog:** [Shockwave Blast Radius agent](https://gitlab.com/explore/ai-catalog/agents/1011457/)

---

## Why

Reviewers approve changes blind to ripple effects. `grep` can't follow a resolved cross-file call graph; Orbit already built one. Shockwave turns that graph into an answer to the only question that matters in review: **"if I change this, what breaks?"**

## What it does

- **`shockwave analyze <symbol|file>`** — transitive inbound impact set (callers → callers-of-callers …), ranked by risk.
- **`shockwave diff <gitref>`** — blast radius of every symbol changed in a diff. The reviewer's killer feature.
- **Reports** — ranked Markdown, a Mermaid graph, and a self-contained HTML view.
- **Risk scoring** — flags high fan-in call sites with **no direct test**, and generates pytest stubs for them.
- **MR bot** — a GitLab CI job that auto-posts the blast-radius review on every merge request ([`.gitlab-ci.yml`](.gitlab-ci.yml) + [`shockwave/ci_bot.py`](shockwave/ci_bot.py)).
- **AI Catalog agent** — ask *"what's the blast radius of `<symbol>`?"* in GitLab Duo (uses Orbit Remote's `query_graph`).

## How it works

```
seed symbol/file ─▶ resolve to gl_definition ─▶ transitive inbound closure
                    over gl_edge (CALLS + cross-file via ImportedSymbol + EXTENDS)
                    ─▶ risk score + direct-test flag ─▶ report / graph
```

Orbit Local indexes a repo into a DuckDB graph (`~/.orbit/graph.duckdb`); Shockwave pulls the call/import edges via `orbit sql` and walks them in Python (cycle-safe BFS). Against **Orbit Remote** it does the same walk over the REST query API (`shockwave analyze --remote`), which the MR bot and AI Catalog agent use.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## See it in action

Run against **Flask** (`pallets/flask`, ~1,650 definitions), asking what depends
on `setupmethod` — a one-line internal decorator:

```text
$ shockwave analyze setupmethod --max-hops 4

# ⚡ Blast radius: `src.flask.sansio.scaffold.setupmethod`

**114** definitions across **10** files depend on this change.
 🔥 **7** high-impact hotspot(s) with **no direct test** need review.

## 🔥 Hotspots with no direct test (review first)
| Definition                                   | File                           | Depth | Fan-in | Risk |
| -------------------------------------------- | ------------------------------ | ----: | -----: | ---: |
| `Blueprint.record_once`                      | src/flask/sansio/blueprints.py |     1 |     10 | 20.0 |
| `Scaffold._method_route`                     | src/flask/sansio/scaffold.py   |     2 |      5 |  5.0 |
| `App.add_template_filter`                    | src/flask/sansio/app.py        |     1 |      2 |  4.0 |
```

Full reports (Markdown / HTML / JSON) are in [`examples/flask/`](examples/flask).

## Quick start

```bash
# 1. Install Orbit Local  (Windows)
irm https://gitlab.com/gitlab-org/orbit/knowledge-graph/-/raw/main/install.ps1 | iex
#    (macOS/Linux)
curl -fsSL "https://gitlab.com/gitlab-org/orbit/knowledge-graph/-/raw/main/install.sh" | bash

# 2. Index a repo
orbit index /path/to/repo

# 3. Install + run Shockwave
pip install -e .
shockwave analyze process_payment --format md
```

### Against Orbit Remote (the hosted graph)

Shockwave also runs against **Orbit Remote** over its REST API — no local index
needed. Because Remote forbids full-graph scans, the blast radius is computed by
*iterative anchored traversal* (one query per hop):

```bash
shockwave analyze compute --remote https://gitlab.com --token "$GITLAB_TOKEN"
```

Example (live `gitlab.com` graph of this very repo):

```text
# ⚡ Blast radius: `shockwave.blast_radius.compute`
**9** definitions across **2** files depend on this change.
  shockwave/cli.py · main
  tests/test_blast_radius.py · test_depths, test_cycle_terminates, …
```

## Status

🚧 Under active development for the hackathon. See the build plan and `docs/`.

## License

[MIT](LICENSE)
