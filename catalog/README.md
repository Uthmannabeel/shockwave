# Publishing Shockwave to the GitLab AI Catalog

This directory holds the two **publishable** Shockwave artifacts for the GitLab
Transcend hackathon (Showcase track):

| File | What it is |
| --- | --- |
| [`agent.yaml`](agent.yaml) | A conversational **agent** — ask *"blast radius of `process_payment`?"* |
| [`flow.yaml`](flow.yaml) | An MR-triggered **flow** that posts a blast-radius review comment |

Both use **Orbit Remote**'s MCP tools (`query_graph`, `get_graph_schema`). The
Python engine in [`../shockwave/`](../shockwave) is the local reference
implementation of the same algorithm (runs against Orbit Local).

## Prerequisites

- A GitLab project where you have the **Maintainer or Owner** role.
- **GitLab Duo Agent Platform** available, and the **Orbit MCP server enabled**
  in that project (Settings → so `query_graph` / `get_graph_schema` appear in the
  Available tools list). Orbit Remote requires Premium/Ultimate.
- For the flow: a tool that can post an MR note enabled in the project.

## Publish the agent

1. **Explore → AI Catalog → Agents → New agent.**
2. Fill the form from [`agent.yaml`](agent.yaml):
   - **Display name** / **Description** → the corresponding fields.
   - **Visibility** → Public.
   - **System prompt** → paste the `system_prompt` block.
   - **Available tools** → select `get_graph_schema` and `query_graph`.
3. **Create agent.** Test it: *"What's the blast radius of `<a function in your repo>`?"*

## Publish the flow

1. **Explore → AI Catalog → Flows → New flow.**
2. Name + description, **Visibility: Public**, paste [`flow.yaml`](flow.yaml) as
   the Flow YAML, **Create flow**.
3. **Enable** the flow in your project and add a **trigger** — e.g.
   *Merge request ready* or *Assign reviewer*.
4. Open/refresh a merge request to trigger it; the flow posts the blast-radius
   comment.

## Notes / known constraints

- Custom flows reject `model`, `name`, `description`, and `product_group` keys
  and require `environment: ambient` — this YAML already complies.
- Tool ids (especially the MR-note tool) can vary per instance; confirm against
  your project's Available tools list and adjust `toolset` if needed.
- Orbit Remote speaks a JSON DSL (not raw SQL); the agent/flow drive it through
  the `query_graph` tool. The equivalent local DuckDB queries are in
  [`../skills/shockwave/recipes`](../skills/shockwave/recipes).
