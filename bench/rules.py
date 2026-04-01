"""Verifiable compliance rules with automated checks.

Each rule has an id, description, automated check function, and severity.
The check function takes generated code (str) and returns True if compliant.
"""

from __future__ import annotations

import re
from typing import Any

COMPLIANCE_RULES: list[dict[str, Any]] = [
    {
        "id": "no-print-debug",
        "description": "Never use print() for debugging",
        "check": lambda code: "print(" not in code,
        "severity": "high",
    },
    {
        "id": "async-io",
        "description": "Use async def for all I/O functions",
        "check": lambda code: (
            not re.search(
                r"(?<!\basync\s)def\s+(fetch|request|download|upload|send|read_url)\(",
                code,
            )
        ),
        "severity": "high",
    },
    {
        "id": "pydantic-models",
        "description": "Use Pydantic BaseModel not raw dict for data structures",
        "check": lambda code: (
            "BaseModel" in code
            if ("class " in code and ("data" in code.lower() or "response" in code.lower()))
            else True
        ),
        "severity": "medium",
    },
    {
        "id": "structlog-only",
        "description": "Use structlog, never import logging or print()",
        "check": lambda code: "import logging" not in code,
        "severity": "high",
    },
    {
        "id": "type-hints",
        "description": "All function signatures must have type hints",
        "check": lambda code: (
            not re.search(r"def \w+\([^)]*\):", code)
            or all(
                re.search(r":\s*\w+", param)
                for line in re.findall(r"def \w+\(([^)]*)\)", code)
                for param in line.split(",")
                if param.strip() and param.strip() != "self"
            )
        ),
        "severity": "medium",
    },
    {
        "id": "no-force-push",
        "description": "Never use git push --force",
        "check": lambda code: "push --force" not in code and "push -f " not in code,
        "severity": "critical",
    },
    {
        "id": "no-secrets",
        "description": "No hardcoded API keys, tokens, or passwords",
        "check": lambda code: not re.search(
            r"(api_key|token|password|secret)\s*=\s*['\"][^'\"]{8,}", code, re.I
        ),
        "severity": "critical",
    },
    {
        "id": "error-handling",
        "description": "External API calls must have try/except",
        "check": lambda code: (
            "try:" in code
            if any(kw in code for kw in ["requests.", "httpx.", "aiohttp.", "urlopen"])
            else True
        ),
        "severity": "medium",
    },
    {
        "id": "no-star-import",
        "description": "Never use from module import *",
        "check": lambda code: "import *" not in code,
        "severity": "low",
    },
    {
        "id": "docstrings",
        "description": "Public functions must have docstrings",
        "check": lambda code: (
            # Check that every top-level def is followed by a docstring
            all(
                '"""' in block or "'''" in block
                for block in re.findall(
                    r"def \w+\([^)]*\)(?:\s*->.*?)?:\s*\n(.*?)(?=\ndef |\nclass |\Z)",
                    code,
                    re.DOTALL,
                )
            )
            if re.search(r"def \w+\(", code)
            else True
        ),
        "severity": "low",
    },
]


def get_rules_by_severity(severity: str) -> list[dict[str, Any]]:
    """Return rules filtered by severity level."""
    return [r for r in COMPLIANCE_RULES if r["severity"] == severity]


def get_rule_by_id(rule_id: str) -> dict[str, Any] | None:
    """Return a single rule by id."""
    for r in COMPLIANCE_RULES:
        if r["id"] == rule_id:
            return r
    return None
