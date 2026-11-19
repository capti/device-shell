"""Machine-readable markers used in issue bodies.

Issue bodies are untrusted data. Only these strict markers are recognised by the
parser; arbitrary text never authorises a write. This module intentionally holds
constants only - no logic, no I/O, no imports beyond the standard library (none).
"""

METADATA_MARKER = "issue-workflow:v1"

CRITERIA_START = "<!-- workflow:criteria:start -->"
CRITERIA_END = "<!-- workflow:criteria:end -->"

ACCEPTANCE_START = "<!-- workflow:acceptance:start -->"
ACCEPTANCE_END = "<!-- workflow:acceptance:end -->"
