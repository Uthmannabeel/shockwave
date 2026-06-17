-- Direct (one-hop) inbound callers of a symbol. Replace {{SYMBOL}}.
-- Covers same-file Definition->Definition calls AND cross-file calls bridged
-- through ImportedSymbol by name.
WITH seed AS (
    SELECT id, name FROM gl_definition WHERE name = '{{SYMBOL}}' OR fqn = '{{SYMBOL}}'
)
-- same-graph callers
SELECT caller.fqn, caller.file_path, 'direct' AS via
FROM gl_edge e
JOIN seed s ON e.target_id = s.id
JOIN gl_definition caller ON caller.id = e.source_id
WHERE e.relationship_kind IN ('CALLS', 'EXTENDS')
  AND e.source_kind = 'Definition'
  AND e.target_kind = 'Definition'
UNION
-- cross-file callers (Definition -> ImportedSymbol, bridged by name)
SELECT caller.fqn, caller.file_path, 'import' AS via
FROM seed s
JOIN gl_imported_symbol sym ON sym.identifier_name = s.name
JOIN gl_edge e ON e.target_id = sym.id
JOIN gl_definition caller ON caller.id = e.source_id
WHERE e.relationship_kind = 'CALLS'
  AND e.target_kind = 'ImportedSymbol'
  AND e.source_kind = 'Definition'
ORDER BY file_path, fqn;
