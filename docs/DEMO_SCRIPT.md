# Demo script (≤ 3:00)

Goal: prove Shockwave answers *"if I change this, what breaks?"* using Orbit.

- **0:00–0:25 — Hook.** "You're about to change one function. What breaks? `grep` can't tell you — but Orbit's knowledge graph can." Open Flask's `setupmethod` — a one-line internal decorator.
- **0:25–1:10 — Analyze.** `shockwave analyze setupmethod`. Reveal the punchline: **114 definitions across 10 files** depend on it; walk the ranked report and the Mermaid graph rippling outward.
- **1:10–1:50 — Risk.** Highlight the **untested high-impact** call sites Shockwave flagged — the ones a reviewer must check.
- **1:50–2:30 — Reviewer flow.** `shockwave diff main` on a real branch → blast radius of the whole change. (If catalog flow is live: show the auto-posted MR comment.)
- **2:30–3:00 — Catalog.** Ask the published AI Catalog agent *"blast radius of <fn>?"*; it issues Orbit `query_graph` calls and returns the same set. Close on the value: review with context, not guesswork.

## Pre-flight checklist
- [ ] `examples/` repo indexed; reports pre-generated as fallback.
- [ ] Terminal font large; colors on.
- [ ] Catalog agent enabled in a demo project.
- [ ] Recording ≤ 3:00, uploaded to YouTube/Vimeo (unlisted ok).
