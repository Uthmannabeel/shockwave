"""Single source of truth for Orbit graph table/column/edge names.

These mirror the Orbit ontology, but the *local* DuckDB build may differ
(e.g. code edges in ``gl_code_edge`` vs a flattened ``gl_edge``; edge-kind
casing). Day-1 task: run ``orbit schema`` against a real indexed repo and
correct anything here. Everything else reads from these constants so a
schema change is a one-file edit.
"""

# --- node tables ---
DEFINITION = "gl_definition"
FILE = "gl_file"
DIRECTORY = "gl_directory"
IMPORTED_SYMBOL = "gl_imported_symbol"

# --- edge table ---
# Confirm on day 1: code relationships are expected in gl_code_edge.
CODE_EDGE = "gl_code_edge"

# edge direction + type columns
EDGE_SOURCE = "source_id"
EDGE_TARGET = "target_id"
EDGE_SOURCE_KIND = "source_kind"
EDGE_TARGET_KIND = "target_kind"
EDGE_KIND = "relationship_kind"

# --- relationship kinds (confirm casing on day 1; ontology uses lowercase) ---
CALLS = "calls"
IMPORTS = "imports"
DEFINES = "defines"
EXTENDS = "extends"
CONTAINS = "contains"

# inbound edge kinds that constitute a blast radius
BLAST_EDGE_KINDS = (CALLS, IMPORTS, EXTENDS)

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
