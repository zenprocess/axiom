"""Verifiable compliance rules with automated regex checks.

Each rule has an id, description, automated check function, and severity.
The check function takes generated code (str) and returns True if compliant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable


@dataclass
class Rule:
    """A single compliance rule with automated check."""

    id: str
    description: str
    check: Callable[[str], bool]
    severity: str  # critical, high, medium, low
    trigger: str  # pattern that triggers the rule
    bad_example: str  # example violation
    good_example: str  # correct usage


RULES: list[Rule] = [
    Rule(
        id="no-print-debug",
        description="Never use print() for debugging or logging",
        check=lambda code: "print(" not in code,
        severity="high",
        trigger="print(",
        bad_example="print(f'debug: {x}')",
        good_example="log.info('debug_value', x=x)",
    ),
    Rule(
        id="async-io",
        description="Use async def for all I/O functions",
        check=lambda code: not re.search(
            r"(?<!\basync\s)def\s+(fetch|request|download|upload|send|read_url)\(",
            code,
        ),
        severity="high",
        trigger="def fetch|request|download|upload|send",
        bad_example="def fetch(url): requests.get(url)",
        good_example="async def fetch(url: str) -> Response: ...",
    ),
    Rule(
        id="pydantic-models",
        description="Use Pydantic BaseModel not raw dict for data structures",
        check=lambda code: (
            "BaseModel" in code
            if ("class " in code and ("data" in code.lower() or "response" in code.lower()))
            else True
        ),
        severity="medium",
        trigger="class with data/response",
        bad_example="user = {'name': 'Alice'}",
        good_example="class User(BaseModel): name: str",
    ),
    Rule(
        id="structlog-only",
        description="Use structlog, never import logging or print()",
        check=lambda code: "import logging" not in code,
        severity="high",
        trigger="import logging",
        bad_example="import logging",
        good_example="import structlog",
    ),
    Rule(
        id="type-hints",
        description="All function signatures must have type hints",
        check=lambda code: (
            not re.search(r"def \w+\([^)]*\):", code)
            or all(
                re.search(r":\s*\w+", param)
                for line in re.findall(r"def \w+\(([^)]*)\)", code)
                for param in line.split(",")
                if param.strip() and param.strip() != "self"
            )
        ),
        severity="medium",
        trigger="def signatures",
        bad_example="def process(data, count):",
        good_example="def process(data: list[str], count: int) -> list[str]:",
    ),
    Rule(
        id="no-force-push",
        description="Never use git push --force",
        check=lambda code: "push --force" not in code and "push -f " not in code,
        severity="critical",
        trigger="git push",
        bad_example="git push --force origin main",
        good_example="git push --force-with-lease origin feature",
    ),
    Rule(
        id="no-secrets",
        description="No hardcoded API keys, tokens, or passwords",
        check=lambda code: not re.search(
            r"(api_key|token|password|secret)\s*=\s*['\"][^'\"]{8,}", code, re.I
        ),
        severity="critical",
        trigger="api_key|token|password assignment",
        bad_example="api_key = 'sk-1234abcd...'",
        good_example="api_key = os.environ['API_KEY']",
    ),
    Rule(
        id="error-handling",
        description="External API calls must have try/except",
        check=lambda code: (
            "try:" in code
            if any(kw in code for kw in ["requests.", "httpx.", "aiohttp.", "urlopen"])
            else True
        ),
        severity="medium",
        trigger="requests.|httpx.|aiohttp.",
        bad_example="resp = requests.get(url)  # no try/except",
        good_example="try:\\n    resp = requests.get(url)\\nexcept RequestException: ...",
    ),
    Rule(
        id="no-star-import",
        description="Never use from module import *",
        check=lambda code: "import *" not in code,
        severity="low",
        trigger="from module import *",
        bad_example="from os.path import *",
        good_example="from os.path import join, exists",
    ),
    Rule(
        id="docstrings",
        description="Public functions must have docstrings",
        check=lambda code: (
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
        severity="low",
        trigger="public def",
        bad_example="def fetch_user(id): return ...",
        good_example='def fetch_user(id: int) -> User:\\n    """Fetch user by ID."""',
    ),
]


def get_rules_by_severity(severity: str) -> list[Rule]:
    """Return rules filtered by severity level."""
    return [r for r in RULES if r.severity == severity]


def get_rule_by_id(rule_id: str) -> Rule | None:
    """Return a single rule by id."""
    for r in RULES:
        if r.id == rule_id:
            return r
    return None
