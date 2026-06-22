# Orbit Reachability skill

Reusable recipes for **graph reachability over GitLab Orbit Remote** — finding
what depends on (or is depended on by) a node, transitively. Orbit's query DSL is
powerful but has non-obvious rules; this skill encodes the ones we learned the
hard way so any agent gets correct results on the first try.

> Any Duo agent or external MCP client can use these. Built by
> [Shockwave](https://github.com/Uthmannabeel/shockwave); contributed back so the
> ecosystem doesn't re-learn the same traversal gotchas.

## The rules that bite you
1. **Endpoint:** `POST /api/v4/orbit/query` with body `{"query": <DSL>, "response_format": "raw"}`. Auth header `PRIVATE-TOKEN`.
2. **`query_type` is `traversal` or `aggregation`** — there is no `search`.
3. **Every query MUST be anchored** by `filters` or `node_ids` on at least one
   node. Orbit rejects unanchored queries to avoid full-table scans — you cannot
   "get all definitions" or "get all CALLS edges".
4. **Code lives in the `Definition` entity**; the inter-definition edges are
   `CALLS` and `EXTENDS`. Orbit **already resolves cross-file calls to direct
   `Definition→Definition` edges**, so you never need an import bridge remotely.
5. **Edge direction:** an edge `from` caller `to` callee means *caller depends on
   callee*. For impact/"who breaks if X changes", walk **inbound** (callers of X).
   For dependency/"what X needs", walk **outbound**.
6. **Ids are strings** in responses but accepted as integers in `node_ids`.

## Recipes (`recipes/`)
- `inbound_callers_by_name.json` — direct callers of a symbol named X.
- `inbound_callers_by_file.json` — callers of every definition in a file.
- `inbound_callers_by_ids.json` — callers of a set of node ids (the hop step).
- `outbound_dependencies_by_ids.json` — what a set of nodes calls.

## Transitive reachability (the algorithm)
Because there are no recursive queries, expand one hop per request:

```
frontier = ids of the seed (resolve via inbound_callers_by_name / _by_file)
seen = set(frontier); depth = {id: 0}
for hop in 1..MAX_HOPS:
    result = query(inbound_callers_by_ids, node_ids=frontier)   # or outbound_*
    next = []
    for edge in result.edges:                 # edge.from_id depends on edge.to_id
        nbr = edge.from_id                     # (use to_id for the outbound direction)
        if nbr not in seen:
            seen.add(nbr); depth[nbr] = hop; next.append(nbr)
    if not next: break
    frontier = next
return depth   # every reachable node with its minimum hop distance
```

Dedup by id, bound by `MAX_HOPS`, and you have a cycle-safe reachable set across
any depth — for code today, and for any Orbit entity/edge type by swapping the
entity and relationship names.
