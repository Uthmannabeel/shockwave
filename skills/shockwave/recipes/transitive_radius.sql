-- Transitive inbound blast radius of a symbol.
-- Replace {{SYMBOL}} with a function/class name or fqn. Adjust depth guard (< 5).
-- Run with: orbit sql --file transitive_radius.sql   (after substituting {{SYMBOL}})
WITH RECURSIVE impacts AS (
    -- caller depends on callee (same-graph CALLS/EXTENDS)
    SELECT e.target_id AS callee, e.source_id AS caller
    FROM gl_edge e
    WHERE e.relationship_kind IN ('CALLS', 'EXTENDS')
      AND e.source_kind = 'Definition'
      AND e.target_kind = 'Definition'
    UNION ALL
    -- cross-file calls bridged through ImportedSymbol by name
    SELECT d.id AS callee, e.source_id AS caller
    FROM gl_imported_symbol sym
    JOIN gl_definition d ON d.name = sym.identifier_name
    JOIN gl_edge e ON e.target_id = sym.id
    WHERE e.relationship_kind = 'CALLS'
      AND e.target_kind = 'ImportedSymbol'
      AND e.source_kind = 'Definition'
),
seed AS (
    SELECT id FROM gl_definition WHERE name = '{{SYMBOL}}' OR fqn = '{{SYMBOL}}'
),
radius(def_id, depth) AS (
    SELECT i.caller, 1
    FROM impacts i JOIN seed s ON i.callee = s.id
    WHERE i.caller <> i.callee
    UNION ALL
    SELECT i.caller, r.depth + 1
    FROM impacts i JOIN radius r ON i.callee = r.def_id
    WHERE r.depth < 5
)
SELECT d.fqn, d.file_path, d.definition_type, MIN(r.depth) AS depth
FROM radius r
JOIN gl_definition d ON d.id = r.def_id
GROUP BY d.fqn, d.file_path, d.definition_type
ORDER BY depth, d.fqn;
