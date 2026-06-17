-- Untested high-impact nodes in the blast radius of {{SYMBOL}}.
-- An affected definition is a "hotspot" when it lives in non-test code, no test
-- file calls it, and at least two things depend on it. Review these first.
WITH RECURSIVE impacts AS (
    SELECT e.target_id AS callee, e.source_id AS caller
    FROM gl_edge e
    WHERE e.relationship_kind IN ('CALLS', 'EXTENDS')
      AND e.source_kind = 'Definition' AND e.target_kind = 'Definition'
    UNION ALL
    SELECT d.id AS callee, e.source_id AS caller
    FROM gl_imported_symbol sym
    JOIN gl_definition d ON d.name = sym.identifier_name
    JOIN gl_edge e ON e.target_id = sym.id
    WHERE e.relationship_kind = 'CALLS'
      AND e.target_kind = 'ImportedSymbol' AND e.source_kind = 'Definition'
),
seed AS (
    SELECT id FROM gl_definition WHERE name = '{{SYMBOL}}' OR fqn = '{{SYMBOL}}'
),
radius(def_id, depth) AS (
    SELECT i.caller, 1 FROM impacts i JOIN seed s ON i.callee = s.id
    WHERE i.caller <> i.callee
    UNION ALL
    SELECT i.caller, r.depth + 1 FROM impacts i JOIN radius r ON i.callee = r.def_id
    WHERE r.depth < 5
),
affected AS (
    SELECT def_id, MIN(depth) AS depth FROM radius GROUP BY def_id
),
fan_in AS (
    SELECT callee AS def_id, COUNT(DISTINCT caller) AS fan_in FROM impacts GROUP BY callee
)
SELECT d.fqn, d.file_path, a.depth, COALESCE(f.fan_in, 0) AS fan_in
FROM affected a
JOIN gl_definition d ON d.id = a.def_id
LEFT JOIN fan_in f ON f.def_id = a.def_id
WHERE COALESCE(f.fan_in, 0) >= 2
  AND lower(d.file_path) NOT LIKE '%test%'
  AND lower(d.file_path) NOT LIKE '%spec%'
ORDER BY fan_in DESC, a.depth;
