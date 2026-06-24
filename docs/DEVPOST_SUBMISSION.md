# Devpost submission — ready to paste

Copy each field into the Devpost form. Track: **Showcase** (target category: **Potential Impact**).

---

## Submission name
```
Shockwave — blast-radius impact analysis on GitLab Orbit
```

## Elevator pitch (tagline)
```
Know what a code change breaks — before you merge. Shockwave reads GitLab Orbit's knowledge graph to map a change's blast radius, exposure, and risk, and tells you the exact tests to run.
```

## Try it out (links)
```
Live site & Blast Monitor: https://shockwave-ochw.vercel.app/
Code (MIT, public):        https://gitlab.com/uthmannabeel-group/Shockwave-project
AI Catalog agent:          https://gitlab.com/explore/ai-catalog/agents/1011457/
Live MR-bot review:        https://gitlab.com/uthmannabeel-group/Shockwave-project/-/merge_requests/1
```

## Demo video
```
<paste your YouTube/Vimeo link here>
```

## Built With
```
python, gitlab-orbit, gitlab-duo, gitlab-ai-catalog, gitlab-ci, flask, duckdb, d3.js, javascript, vercel, rest-api
```

---

## Project story (paste into "Tell us about your project")

### Inspiration
Every reviewer has approved a one-line change that quietly broke something three files away. The honest question in code review — *“if I change this, what actually breaks?”* — is one `grep` can't answer, because the answer lives in the **resolved call graph**, not in the text. GitLab Orbit just built that graph. We wanted to turn it into the answer — and then act on it.

### What it does
Point Shockwave at a function, file, or merge-request diff and it traverses Orbit's knowledge graph to tell you:

- **Blast radius** — every definition that transitively depends on the change, across files, ranked by fan-in × proximity.
- **Exposure** — whether the change is *reachable from a public entry point* (route / API / CLI), with the exact call path — so you know if a break is externally observable or internal-only.
- **Untested hotspots** — high fan-in code no test calls directly, each with a generated **pytest stub**.
- **Risk verdict** — one **LOW / REVIEW / HIGH** score the MR bot can gate on.
- **Test impact selection** — the tests that *actually exercise* the change, as a copy-paste `pytest …` command (run those, not the whole suite).
- **Outbound dependencies** — the flip side: what the change relies on.

It ships across **five surfaces**: a CLI, an interactive web **Blast Monitor**, an autonomous **merge-request bot**, a **GitLab Duo agent** in the AI Catalog, and a reusable **Orbit Reachability skill** for the ecosystem.

### How we built it
A small, tested Python engine with **two Orbit backends**: **Orbit Local** (DuckDB graph via `orbit sql`) and **Orbit Remote** (the hosted graph over the JSON traversal DSL). Because Remote forbids full-graph scans, the transitive radius is an **iterative anchored BFS** — one query per hop. On top: a GitLab CI bot that posts the review on MRs, a Duo agent driving Orbit's `query_graph` tool, a D3 web app, and a static export deployed to Vercel (with real baked analyses so the demo works with no backend).

### Challenges we ran into
- **Orbit Local ≠ Remote:** Local flattens code edges into `gl_edge` (no `gl_code_edge`) and has no `ImportedSymbol→Definition` edge, so cross-file calls are bridged by name (disambiguated by `import_path`); Remote resolves them to direct edges but rejects unbounded queries.
- **Honesty under scrutiny:** “untested” overstated a heuristic that only checks *direct* test callers — we reworded it and switched to word-boundary matching to kill false positives.
- **Security reachability** can't be Orbit-native yet: the `Finding` node carries no code location, so it needs a join with GitLab's Vulnerability API (roadmap).
- Plus corporate-network TLS, protected-branch Git, and GitLab.com's runner-verification gate.

### Accomplishments that we're proud of
Two **genuine** Orbit integrations (Local + Remote) with verifiable results — changing Flask's one-line `setupmethod` lights up **114 definitions across 10 files**. A **real, autonomous MR review** posted from the live graph. A published agent, a reusable skill, 23 passing tests, and a tool that's **honest about its own limits**.

### What we learned
A knowledge graph turns review from *“I think this is safe”* into *“here's exactly what depends on it.”* The hard part isn't the traversal — it's being precise about what the graph does and doesn't say.

### What's next
- **Security reachability triage** — rank vulnerabilities by whether they're reachable, via the Vulnerability-API join.
- Line-level diff seeding, more edge types and languages, and an IDE gutter that shows blast radius as you type.

### Limitations (we're explicit)
Static analysis (no dynamic dispatch/reflection/config), signals not guarantees, bounded by Orbit's index (default branch, supported languages, permission-aware on Remote), depth-capped. The tool flags its own caveats — partial results, ambiguous names, the indexed commit — rather than hiding them.
