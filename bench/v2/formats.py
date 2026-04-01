"""Generate compliance rules in all three benchmark formats.

Formats:
- markdown: Verbose prose with examples and rationale (~1195 tokens)
- toon: Axiom S/D tabular rows (~159 tokens)
- cacp: CONTEXT/SCOPE/RULES/VERIFY structured sections (~300 tokens)
"""

from __future__ import annotations

from rules import Rule


# ---------------------------------------------------------------------------
# Markdown — verbose prose (baseline, high token count)
# ---------------------------------------------------------------------------

_RULE_DETAILS: dict[str, str] = {
    "no-print-debug": (
        "Never use `print()` statements for debugging or logging purposes. "
        "Print statements pollute stdout, are not structured, cannot be filtered "
        "by log level, and often get accidentally committed to production code.\n\n"
        "Instead, use the project's structured logging library.\n\n"
        "**Bad:**\n```python\nprint(f'User {user_id} not found')\n```\n\n"
        "**Good:**\n```python\nlog.warning('user_not_found', user_id=user_id)\n```"
    ),
    "async-io": (
        "All functions that perform I/O operations (network requests, file reads, "
        "database queries) MUST be declared with `async def`. Synchronous I/O blocks "
        "the event loop and degrades performance for all concurrent operations.\n\n"
        "This applies to any function named fetch, request, download, upload, send, "
        "or read_url, as well as any function that makes HTTP calls or reads from "
        "external services.\n\n"
        "**Bad:**\n```python\ndef fetch_user(user_id: int):\n    return requests.get(f'/users/{user_id}')\n```\n\n"
        "**Good:**\n```python\nasync def fetch_user(user_id: int) -> User:\n    async with httpx.AsyncClient() as client:\n        resp = await client.get(f'/users/{user_id}')\n        return User(**resp.json())\n```"
    ),
    "pydantic-models": (
        "Use Pydantic `BaseModel` subclasses for all data structures, especially "
        "API response models, configuration objects, and any class that holds "
        "structured data. Never use raw `dict` or `TypedDict` for data that crosses "
        "module boundaries.\n\n"
        "Pydantic provides runtime validation, serialization, and clear schema "
        "documentation. Raw dicts are error-prone and lack type safety.\n\n"
        "**Bad:**\n```python\nuser = {'name': 'Alice', 'email': 'alice@example.com'}\n```\n\n"
        "**Good:**\n```python\nclass User(BaseModel):\n    name: str\n    email: str\n```"
    ),
    "structlog-only": (
        "Use `structlog` for all logging. Never `import logging` from the standard "
        "library and never use `print()` for log output. structlog provides structured "
        "JSON output, automatic context binding, and composable processors.\n\n"
        "The standard `logging` module produces unstructured text that is difficult "
        "to parse, filter, and aggregate in production monitoring systems.\n\n"
        "**Bad:**\n```python\nimport logging\nlogger = logging.getLogger(__name__)\nlogger.info('Processing request')\n```\n\n"
        "**Good:**\n```python\nimport structlog\nlog = structlog.get_logger()\nlog.info('processing_request', request_id=req.id)\n```"
    ),
    "type-hints": (
        "All function signatures must include type hints for parameters and return "
        "values. This applies to all functions, including private helpers and lambdas "
        "assigned to variables. Type hints enable static analysis, IDE support, and "
        "serve as inline documentation.\n\n"
        "**Bad:**\n```python\ndef process(data, count):\n    return data[:count]\n```\n\n"
        "**Good:**\n```python\ndef process(data: list[str], count: int) -> list[str]:\n    return data[:count]\n```"
    ),
    "no-force-push": (
        "NEVER use `git push --force` or `git push -f`. Force pushing rewrites "
        "remote history and can destroy other developers' work. If you need to update "
        "a branch, use `git push --force-with-lease` which is safer, or better yet, "
        "create a new commit.\n\n"
        "This rule has no exceptions. Even on feature branches, force push can cause "
        "data loss if another developer has based work on your commits."
    ),
    "no-secrets": (
        "NEVER hardcode API keys, tokens, passwords, or other secrets in source code. "
        "This includes test files, example code, and documentation. Secrets in code "
        "get committed to version control and are extremely difficult to fully remove.\n\n"
        "Use environment variables, secret management services (Vault, AWS Secrets "
        "Manager), or `.env` files (which must be in `.gitignore`).\n\n"
        "**Bad:**\n```python\napi_key = 'sk-1234567890abcdef'\n```\n\n"
        "**Good:**\n```python\napi_key = os.environ['API_KEY']\n```"
    ),
    "error-handling": (
        "All external API calls must be wrapped in try/except blocks. External "
        "services are unreliable -- they time out, return errors, change their APIs, "
        "and go down for maintenance. Unhandled exceptions from HTTP calls crash the "
        "application.\n\n"
        "Handle at minimum: connection errors, timeout errors, and unexpected status "
        "codes. Log the error with context and either retry or raise a domain-specific "
        "exception.\n\n"
        "**Bad:**\n```python\nresponse = requests.get(url)\ndata = response.json()\n```\n\n"
        "**Good:**\n```python\ntry:\n    response = requests.get(url, timeout=30)\n    response.raise_for_status()\nexcept requests.RequestException as e:\n    log.error('api_call_failed', url=url, error=str(e))\n    raise\n```"
    ),
    "no-star-import": (
        "Never use `from module import *`. Star imports pollute the namespace, make "
        "it impossible to determine where a name was defined, and can silently shadow "
        "existing names. Always import specific names or use the module prefix.\n\n"
        "**Bad:**\n```python\nfrom os.path import *\n```\n\n"
        "**Good:**\n```python\nfrom os.path import join, exists\n```"
    ),
    "docstrings": (
        "All public functions and methods must have docstrings. Docstrings should "
        "describe what the function does, its parameters, return value, and any "
        "exceptions it raises. Use Google-style or NumPy-style docstring format "
        "consistently throughout the project.\n\n"
        "Private functions (prefixed with _) are encouraged but not required to have "
        "docstrings. Class docstrings are always required."
    ),
}


def generate_markdown_rules(rules: list[Rule]) -> str:
    """Generate verbose markdown rules (~1195 tokens).

    Mimics how rules are typically written in CLAUDE.md files: prose
    explanations, rationale, examples, and do/don't blocks.
    """
    lines: list[str] = [
        "# Development Rules",
        "",
        "Follow these rules strictly in all code you write.",
        "",
    ]
    for rule in rules:
        lines.append(f"## {rule.id}")
        lines.append(f"**Severity**: {rule.severity}")
        lines.append("")
        detail = _RULE_DETAILS.get(rule.id, rule.description)
        lines.append(detail)
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# TOON — Axiom S/D tabular format (compressed, low token count)
# ---------------------------------------------------------------------------

_SEVERITY_TO_EFFECT: dict[str, str] = {
    "critical": "MUST_NOT",
    "high": "MUST_NOT",
    "medium": "MUST",
    "low": "SHOULD",
}


def generate_toon_rules(rules: list[Rule]) -> str:
    """Generate TOON tabular rules (~159 tokens).

    Uses Axiom S/D row format with RULES{id,level,effect,instruction,trigger}: header.
    Rules sorted by severity for salience.
    """
    severity_order = ["critical", "high", "medium", "low"]
    sorted_rules = sorted(rules, key=lambda r: severity_order.index(r.severity))

    rows: list[str] = []
    for rule in sorted_rules:
        effect = _SEVERITY_TO_EFFECT.get(rule.severity, "INFO")
        rows.append(
            f"{rule.id},{rule.severity},{effect},{rule.description},{rule.trigger}"
        )

    header = f"RULES[{len(rows)}]{{id,level,effect,instruction,trigger}}:"
    return header + "\n" + "\n".join(rows) + "\n"


# ---------------------------------------------------------------------------
# CACP — Structured sections with bullet points (mid-range tokens)
# ---------------------------------------------------------------------------


def generate_cacp_rules(rules: list[Rule]) -> str:
    """Generate CACP-structured rules (~300 tokens).

    Uses CONTEXT/SCOPE/RULES/VERIFY sections with bullet points.
    More structured than markdown, more readable than TOON.
    """
    sections: list[str] = []

    # CONTEXT
    sections.append("CONTEXT: Python development with strict coding standards.")
    sections.append("")

    # SCOPE
    sections.append("SCOPE: All generated code must comply with the following rules.")
    sections.append("")

    # RULES grouped by severity
    sections.append("RULES:")
    for sev in ["critical", "high", "medium", "low"]:
        sev_rules = [r for r in rules if r.severity == sev]
        if sev_rules:
            sections.append(f"  [{sev.upper()}]")
            for rule in sev_rules:
                effect = _SEVERITY_TO_EFFECT.get(rule.severity, "INFO")
                sections.append(f"  - {rule.id}: {effect} {rule.description}")
    sections.append("")

    # VERIFY
    sections.append("VERIFY:")
    sections.append("- No print() statements in output")
    sections.append("- All I/O functions use async def")
    sections.append("- Data models use Pydantic BaseModel")
    sections.append("- Logging uses structlog only")
    sections.append("- All function signatures have type hints")
    sections.append("- No git push --force")
    sections.append("- No hardcoded secrets")
    sections.append("- External calls wrapped in try/except")
    sections.append("- No star imports")
    sections.append("- Public functions have docstrings")

    return "\n".join(sections) + "\n"


# ---------------------------------------------------------------------------
# TOON + self-commitment priming (pre-dispatch technique)
# ---------------------------------------------------------------------------


def generate_toon_primed_rules(rules: list[Rule]) -> str:
    """TOON format with self-commitment priming prefix.

    Research hypothesis: explicit self-commitment ("I will NOT...")
    before rules improves compliance via constitutional AI principles.
    """
    toon = generate_toon_rules(rules)
    commitments = []
    for r in rules:
        if r.id == "no-print-debug":
            commitments.append("I will use structlog for ALL output, NEVER print()")
        elif r.id == "async-io":
            commitments.append("I will use async def for ALL I/O functions")
        elif r.id == "no-force-push":
            commitments.append("I will NEVER use git push --force")
        elif r.id == "no-secrets":
            commitments.append("I will NEVER hardcode secrets, keys, or passwords")
        elif r.id == "structlog-only":
            commitments.append("I will import structlog, NEVER import logging")
    primer = "Before writing code, I commit to these constraints:\n"
    primer += "\n".join(f"- {c}" for c in commitments)
    primer += "\n\n"
    return primer + toon


# ---------------------------------------------------------------------------
# TOON + few-shot violation examples
# ---------------------------------------------------------------------------


_VIOLATION_EXAMPLES: dict[str, str] = {
    "no-print-debug": "BAD: print(result)  GOOD: log.info('result', data=result)",
    "async-io": "BAD: def fetch(url):  GOOD: async def fetch(url):",
    "no-force-push": "BAD: git push --force  GOOD: git push --force-with-lease",
    "structlog-only": "BAD: import logging  GOOD: import structlog",
    "no-secrets": 'BAD: api_key="sk-abc123"  GOOD: api_key=os.environ["API_KEY"]',
    "error-handling": "BAD: requests.get(url)  GOOD: try: requests.get(url) except: ...",
}


def generate_toon_examples_rules(rules: list[Rule]) -> str:
    """TOON format with violation examples appended.

    Shows the model exact patterns to avoid alongside the rules.
    Costs ~80 extra tokens but may close compliance gap.
    """
    toon = generate_toon_rules(rules)
    examples = "\n\nVIOLATION EXAMPLES:\n"
    for r in rules:
        ex = _VIOLATION_EXAMPLES.get(r.id)
        if ex:
            examples += f"  {r.id}: {ex}\n"
    return toon + examples


# ---------------------------------------------------------------------------
# Format dispatcher
# ---------------------------------------------------------------------------

FORMAT_GENERATORS: dict[str, callable] = {
    "markdown": generate_markdown_rules,
    "toon": generate_toon_rules,
    "cacp": generate_cacp_rules,
    "toon_primed": generate_toon_primed_rules,
    "toon_examples": generate_toon_examples_rules,
}


def generate_rules(format_name: str, rules: list[Rule]) -> str:
    """Generate rules in the specified format."""
    gen = FORMAT_GENERATORS.get(format_name)
    if gen is None:
        raise ValueError(f"Unknown format: {format_name}. Use one of {list(FORMAT_GENERATORS)}")
    return gen(rules)
