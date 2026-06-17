"""Single source of truth for Orbit graph table/column/edge names.

Confirmed against **Orbit Local 0.75.1** via ``orbit schema`` / ``orbit sql``
on a real indexed repo:
  * code edges live in a single flattened ``gl_edge`` table (there is *no*
    ``gl_code_edge`` locally);
  * ``relationship_kind`` values are UPPERCASE (``CALLS``, ``IMPORTS``, ...);
  * node kinds are PascalCase (``Definition``, ``File``, ``ImportedSymbol``);
  * there is no ``ImportedSymbol -> Definition`` resolution edge — cross-file
    calls are ``Definition --CALLS--> ImportedSymbol`` and must be bridged back
    to the concrete definition by name (see ``identifier_name`` / ``import_path``).
Everything else reads from these constants so a schema change is a one-file edit.
"""

# --- node tables ---
DEFINITION = "gl_definition"
FILE = "gl_file"
DIRECTORY = "gl_directory"
IMPORTED_SYMBOL = "gl_imported_symbol"

# --- edge table (local: a single flattened gl_edge) ---
EDGE = "gl_edge"

# edge direction + type columns
EDGE_SOURCE = "source_id"
EDGE_TARGET = "target_id"
EDGE_SOURCE_KIND = "source_kind"
EDGE_TARGET_KIND = "target_kind"
EDGE_KIND = "relationship_kind"

# --- relationship kinds (UPPERCASE in local DuckDB) ---
CALLS = "CALLS"
IMPORTS = "IMPORTS"
DEFINES = "DEFINES"
EXTENDS = "EXTENDS"
CONTAINS = "CONTAINS"

# --- node kinds (PascalCase) ---
KIND_DEFINITION = "Definition"
KIND_FILE = "File"
KIND_IMPORTED_SYMBOL = "ImportedSymbol"
KIND_DIRECTORY = "Directory"

# inbound edge kinds that constitute a blast radius
BLAST_EDGE_KINDS = (CALLS, IMPORTS, EXTENDS)

# --- imported-symbol columns (cross-file resolution bridge) ---
IMP_IDENTIFIER = "identifier_name"
IMP_ALIAS = "identifier_alias"
IMP_PATH = "import_path"
IMP_FILE_PATH = "file_path"

# --- definition columns ---
DEF_ID = "id"
DEF_NAME = "name"
DEF_FQN = "fqn"
DEF_TYPE = "definition_type"
DEF_FILE_PATH = "file_path"  # NB: definitions link to files by path string, not id
DEF_START_LINE = "start_line"
DEF_END_LINE = "end_line"

# heuristics for detecting test files in a blast radius
TEST_PATH_MARKERS = ("test", "spec", "__tests__", ".test.", ".spec.", "_test")
