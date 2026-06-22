# Shockwave — Devpost submission

**Tagline:** See the blast radius of a code change *before* it merges.

**Track:** Showcase · **Primary category:** Potential Impact

**Links**
- Code (MIT): https://github.com/Uthmannabeel/shockwave
- AI Catalog agent: https://gitlab.com/explore/ai-catalog/agents/1011457/
- Live MR bot comment (real): https://gitlab.com/uthmannabeel-group/Shockwave-project/-/merge_requests/1
- Demo video: _<paste YouTube/Vimeo link>_

---

## Inspiration
Every reviewer has approved a one-line change that quietly broke something three files away. The honest question in code review — *"if I change this, what actually breaks?"* — is one `grep` can't answer, because the answer lives in the **resolved cross-file call graph**, not in text. GitLab Orbit already builds that graph. Shockwave turns it into the answer.

## What it does
Point Shockwave at a function, file, or merge-request diff and it traverses Orbit's knowledge graph to compute the **transitive blast radius** — every definition that depends on the change, across files — and then:
- **ranks by risk** (fan-in × proximity), and
- runs **exposure analysis** — does the change's blast radius reach a **public entry point** (route / API / CLI / `main`)? If so a break is *externally observable*, not internal-only — and we show the exact **call path** from the entry point to the change. (This is the same *reachability* question security triage asks: "can the outside actually reach this code?")
- **flags hotspots with no direct test** — high-impact code that no test calls directly, the stuff most likely to break silently, and
- **generates a pytest stub** for each one, so you know exactly what to pin down first.

It ships in three forms:
1. **CLI** — `shockwave analyze <symbol|file>` and `shockwave diff <ref>`, against **Orbit Local** *or* **Orbit Remote** (`--remote`). Outputs Markdown, an interactive HTML/Mermaid graph, or JSON.
2. **MR bot** — a GitLab CI job that, on every merge request, auto-posts the blast-radius review as a comment (computed from the live Orbit Remote graph). *Intelligent orchestration, now with context.*
3. **AI Catalog agent** — ask GitLab Duo *"what's the blast radius of `X`?"* in natural language.

## How we built it
- A small, well-tested **Python engine**. The core is a cycle-safe inbound BFS over Orbit's `CALLS`/`EXTENDS` edges.
- **Orbit Local backend** — queries the local DuckDB graph via `orbit sql`; resolves cross-file calls through the `ImportedSymbol` node, disambiguated by `import_path`.
- **Orbit Remote backend** — speaks Orbit's JSON **traversal DSL** over `POST /api/v4/orbit/query`. Because Remote forbids full-graph scans, the blast radius is an **iterative anchored BFS**: resolve the seed by filter, then expand outward by `node_ids`, one hop per query.
- **GitLab CI bot** (`ci_bot.py`) — reads the MR's changed files, runs the remote analysis, and upserts a review comment via the GitLab API.
- **AI Catalog agent + flow** — system prompts that drive Orbit's `query_graph`/`get_graph_schema` tools.

## Challenges we ran into
- **Orbit Local ≠ Orbit Remote.** Local flattens code edges into `gl_edge` (no `gl_code_edge`), stores `relationship_kind` uppercase, and has **no `ImportedSymbol → Definition` edge** — so cross-file calls must be bridged by name. Remote, by contrast, **resolves cross-file calls to direct edges** but **rejects unbounded queries**. We built two backends that produce one honest answer.
- **Name collisions.** Bridging cross-file calls by name alone conflated same-named symbols (`get`, `__init__`); we disambiguate by `import_path`.
- **Honesty under audit.** "Untested" overstated a heuristic that only checks *direct* test callers — we reworded it to "no direct test" everywhere.
- Corporate TLS interception (solved with `truststore`) and protected-branch Git flows along the way.

## Accomplishments we're proud of
- **Two genuine Orbit integrations** (Local + Remote), both producing verifiable, reproducible results — e.g. changing Flask's one-line `setupmethod` decorator lights up **114 definitions across 10 files**.
- A **real, autonomous MR review** posted from the live graph — not a mock.
- Code that **survives a senior-level audit**: tested, accurate claims, no overstatement.

## What we learned
A knowledge graph changes review from *"I think this is safe"* to *"here is exactly what depends on it."* The hard part isn't the traversal — it's being honest about what the graph does and doesn't say.

## Giving back to the ecosystem
Orbit's traversal DSL is powerful but unforgiving — every query must be anchored,
full scans are rejected, and cross-file calls are pre-resolved. We packaged the
patterns we learned as a reusable **[Orbit Reachability skill](https://github.com/Uthmannabeel/shockwave/blob/main/skills/orbit-reachability/SKILL.md)**:
the DSL rules, ready JSON recipes, and the hop-by-hop transitive-reachability
algorithm. Any Duo agent or MCP client can now do correct graph reachability over
Orbit — for code today, any entity/edge tomorrow — without re-learning the gotchas.

## What's next
- **Security reachability triage** — the natural next step: rank vulnerabilities by
  whether their code is *reachable from an entry point* and show the blast radius of
  a fix. Orbit's graph doesn't yet carry a finding's code location (the `Finding`
  node has no file/line, and there's no `Finding→Definition` edge), so this means
  joining Orbit reachability with GitLab's Vulnerability API by location — exactly
  the bridge Shockwave is built to be.
- Line-level MR seeding (map diff hunks to the exact changed definitions).
- More edge types (overrides, data-flow) and languages.
- An IDE gutter that shows a symbol's blast radius + exposure as you type.

## Built with
Python · GitLab Orbit (Local + Remote) · GitLab Duo AI Catalog · GitLab CI/CD · DuckDB · the Orbit query DSL · requests · truststore
