# Demo script (≤ 3:00)

Goal: prove Shockwave answers *"if I change this, what breaks?"* using the Orbit
knowledge graph — and that it acts on the answer (flags untested hotspots,
suggests tests, comments on the MR).

**Before recording**
- [ ] Index Flask locally: `orbit index C:\path\to\flask` (≈1,650 defs).
- [ ] A fresh GitLab PAT in `$env:GITLAB_TOKEN` for the `--remote` shot.
- [ ] MR !1 open in a browser tab (the bot comment is already posted).
- [ ] Terminal font large; colors on; window cropped clean.

---

### 0:00–0:20 — The hook
> "You're reviewing a one-line change to a function. What does it break? `grep`
> can't tell you — it can't follow a resolved cross-file call graph. But GitLab
> Orbit already built one. This is Shockwave."

Show Flask's `setupmethod` in the editor — *"a tiny internal decorator."*

### 0:20–1:05 — Analyze (local Orbit)
Run:
```
shockwave analyze setupmethod --max-hops 4
```
> "Change that one decorator and **114 definitions across 10 files** are in the
> blast radius. Seven of them are high fan-in and **no test touches them
> directly** — the silent-break risks."

Scroll the ranked report; open the HTML view (`--format html`) to show the
Mermaid graph rippling outward.

### 1:05–1:25 — Exposure (the novel beat)
Scroll to **🚪 Exposure**.
> "And it's not just *what* depends on it — Shockwave shows the change is
> **reachable from a public entry point**: Flask's `@route` decorator.
> The exact call path: `Scaffold.route → setupmethod`. A break here is
> externally observable, not internal. That's the same reachability question
> security triage asks — applied to change risk."

### 1:25–1:50 — Verdict + the tests to run
Point to the **risk badge** (HIGH 100/100) and the **✅ Tests to run** panel.
> "It doesn't stop at analysis — it gives a verdict: HIGH risk. And instead of
> running the whole suite, it tells you the **58 tests that actually exercise
> this change** — copy, paste, run. Plus a generated stub for the hotspots that
> have no test at all."

### 1:35–2:05 — Same graph, in the cloud (Orbit Remote)
Run:
```
shockwave analyze compute --remote https://gitlab.com --token $env:GITLAB_TOKEN
```
> "Same engine, no local index — this is querying the hosted Orbit graph live
> over its REST API. Real callers, indexed facts, not guesses."

### 2:05–2:45 — The autonomous reviewer (the payoff)
Switch to the **MR !1** browser tab; scroll to Shockwave's comment.
> "Now put it in the pipeline. Open a merge request and Shockwave's bot posts
> this review automatically — the blast radius, the untested hotspots, the test
> stubs — straight from Orbit. Intelligent orchestration, with context."

### 2:45–3:00 — Close
Show the published **AI Catalog agent** page (or ask it a blast-radius question).
> "Available as a CLI, a CI bot, and a GitLab Duo agent in the AI Catalog. Review
> with context, not guesswork. That's Shockwave."

---

## One-line value statement (for the description / thumbnail)
*Shockwave reads GitLab Orbit's knowledge graph to show the blast radius of a
change before it merges — and auto-reviews every MR with the risks and the tests
you're missing.*

## Fallback (if a live call hiccups)
Pre-generated reports are committed in `examples/flask/` and the MR comment is
already posted on MR !1 — the demo is reproducible offline.
