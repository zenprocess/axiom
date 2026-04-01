"""Tunable Axiom format parameters.

This is the file that the autoresearch loop modifies. Each parameter
controls how rules are compiled into the Axiom S/D representation
that gets injected as system prompt context.

The runner compares Axiom output (using these parameters) against
a raw markdown baseline to measure compliance_rate and token_count.
"""

from __future__ import annotations

# --- Axiom format parameters — tune these for maximum compliance ---

# TOON header template: {count} = number of rows, columns in braces
HEADER_TEMPLATE: str = "RULES{{id,instruction}}:"

# Maximum words for the S (summary) row instruction
SUMMARY_MAX_WORDS: int = 15

# Maximum words for the D (detail) row instruction
DETAIL_MAX_WORDS: int = 30

# Whether to include trigger column values
INCLUDE_TRIGGER: bool = False

# Whether to include D (detail) rows at all
INCLUDE_DETAIL: bool = False

# Allowed effect vocabulary for encoding
EFFECT_VOCABULARY: set[str] = {"MUST_NOT", "MUST", "SHOULD", "INFO"}

# Separator between S and D rows (empty = no separator)
ROW_SEPARATOR: str = ""

# Whether to group rules by severity in output
GROUP_BY_SEVERITY: bool = True

# Optional preamble text before the table (empty = no preamble)
PREAMBLE: str = ""

# Optional example column with violation patterns
INCLUDE_EXAMPLE: bool = False
