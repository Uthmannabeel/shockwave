-- Resolve a symbol name or fqn to definition(s). Replace {{SYMBOL}}.
SELECT id, name, fqn, definition_type, file_path, start_line, end_line
FROM gl_definition
WHERE name = '{{SYMBOL}}'
   OR fqn = '{{SYMBOL}}'
   OR fqn LIKE '%.' || '{{SYMBOL}}'
ORDER BY fqn;
