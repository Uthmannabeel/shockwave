# Shockwave ⚡

**See the blast radius of a code change before it merges.**

Shockwave is a blast-radius impact-analysis tool built on the [GitLab Orbit](https://about.gitlab.com/gitlab-orbit/) knowledge graph. Point it at a changed function, file, or git diff and it traverses Orbit's resolved code graph — calls, imports, and inheritance — to show you *everything* a change can ripple into: every caller, the tests that should re-run, and the highest-risk **untested** call sites, ranked.

> Built for the **GitLab Transcend Hackathon** (Showcase track).

---

## Why

Reviewers approve changes blind to ripple effects. `grep` can't follow a resolved cross-file call graph; Orbit already built one. Shockwave turns that graph into an answer to the only question that matters in review: **"if I change this, what breaks?"**

## What it does

- **`shockwave analyze <symbol|file>`** — transitive inbound impact set (callers → callers-of-callers …), ranked by risk.
- **`shockwave diff <gitref>`** — blast radius of every symbol changed in a diff. The reviewer's killer feature.
- **Reports** — ranked Markdown, a Mermaid graph, and a self-contained HTML view.
- **Risk scoring** — flags high-impact, **untested** call sites.
- **AI Catalog agent** — ask *"what's the blast radius of `process_payment`?"* in GitLab Duo (uses Orbit Remote's `query_graph`).

## How it works

```
seed symbol/file ─▶ resolve to gl_definition ─▶ transitive inbound closure
                    over gl_code_edge (calls + imports↔ImportedSymbol + extends)
                    ─▶ risk score + test-coverage flag ─▶ report / graph
```

Orbit Local indexes a repo into a DuckDB graph (`~/.orbit/graph.duckdb`); Shockwave runs `WITH RECURSIVE` traversals against it via `orbit sql`. The same logic ships as a GitLab Duo agent for Orbit Remote.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

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

## Status

🚧 Under active development for the hackathon. See the build plan and `docs/`.

## License

[MIT](LICENSE)
