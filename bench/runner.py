#!/usr/bin/env python3
"""Compliance validation runner — A/B and autoresearch modes.

Usage:
    python scripts/compliance/runner.py --mode ab          # A/B comparison
    python scripts/compliance/runner.py --mode autoresearch # autonomous tuning loop
    python scripts/compliance/runner.py --mode ab --task http-client  # single task
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import tiktoken

# Ensure script directory is importable
_script_dir = Path(__file__).resolve().parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

from rules import COMPLIANCE_RULES
from tasks import TASKS
from format import (
    DETAIL_MAX_WORDS,
    EFFECT_VOCABULARY,
    GROUP_BY_SEVERITY,
    HEADER_TEMPLATE,
    INCLUDE_DETAIL,
    INCLUDE_EXAMPLE,
    INCLUDE_TRIGGER,
    PREAMBLE,
    ROW_SEPARATOR,
    SUMMARY_MAX_WORDS,
)

SCRIPT_DIR = Path(__file__).parent
RESULTS_TSV = SCRIPT_DIR / "results.tsv"
OUTPUT_DIR = SCRIPT_DIR / "output"


# ---------------------------------------------------------------------------
# Rule format generators
# ---------------------------------------------------------------------------


def _truncate(text: str, max_words: int) -> str:
    """Truncate text to max_words."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def _effect_for_rule(rule: dict[str, Any]) -> str:
    """Map rule severity to an Axiom effect verb."""
    severity_map: dict[str, str] = {
        "critical": "MUST_NOT",
        "high": "MUST_NOT",
        "medium": "MUST",
        "low": "SHOULD",
    }
    effect = severity_map.get(rule["severity"], "INFO")
    if effect not in EFFECT_VOCABULARY:
        effect = "inform"
    return effect


def _trigger_for_rule(rule: dict[str, Any]) -> str:
    """Infer a trigger string from rule description."""
    triggers: dict[str, str] = {
        "no-print-debug": "print(",
        "async-io": "def fetch|request|download|upload|send",
        "pydantic-models": "class with data/response",
        "structlog-only": "import logging",
        "type-hints": "def signatures",
        "no-force-push": "git push",
        "no-secrets": "api_key|token|password assignment",
        "error-handling": "requests.|httpx.|aiohttp.",
        "no-star-import": "from module import *",
        "docstrings": "public def",
    }
    return triggers.get(rule["id"], "")


def _example_for_rule(rule: dict[str, Any]) -> str:
    """Return a short violation example for the rule."""
    examples: dict[str, str] = {
        "no-print-debug": "print(f'debug: {x}')",
        "async-io": "def fetch(url): requests.get(url)",
        "pydantic-models": "user = {'name': 'Alice'}",
        "structlog-only": "import logging",
        "type-hints": "def process(data, count):",
        "no-force-push": "git push --force origin main",
        "no-secrets": "api_key = 'sk-1234abcd...'",
        "error-handling": "resp = requests.get(url) # no try/except",
        "no-star-import": "from os.path import *",
        "docstrings": "def fetch_user(id): return ...",
    }
    return examples.get(rule["id"], "")


def write_markdown_rules(rules: list[dict[str, Any]], out_path: Path) -> Path:
    """Write rules as conventional verbose markdown instructions.

    This mimics how rules are typically written in CLAUDE.md files: prose
    explanations, rationale, examples, and do/don't blocks. The verbosity
    is the point — Axiom S/D compresses this down.
    """
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
            "services are unreliable — they time out, return errors, change their APIs, "
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

    lines: list[str] = [
        "# Development Rules",
        "",
        "Follow these rules strictly in all code you write.",
        "",
    ]
    for rule in rules:
        lines.append(f"## {rule['id']}")
        lines.append(f"**Severity**: {rule['severity']}")
        lines.append("")
        detail = _RULE_DETAILS.get(rule["id"], rule["description"])
        lines.append(detail)
        lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines))
    return out_path


def write_axiom_rules(rules: list[dict[str, Any]], out_path: Path) -> Path:
    """Write rules in Axiom S/D tabular format using current format.py params."""
    rows: list[str] = []

    # Optionally group by severity
    if GROUP_BY_SEVERITY:
        severity_order = ["critical", "high", "medium", "low"]
        sorted_rules = sorted(rules, key=lambda r: severity_order.index(r["severity"]))
    else:
        sorted_rules = list(rules)

    for rule in sorted_rules:
        effect = _effect_for_rule(rule)
        summary = _truncate(rule["description"], SUMMARY_MAX_WORDS)
        trigger = _trigger_for_rule(rule) if INCLUDE_TRIGGER else ""

        if INCLUDE_TRIGGER:
            s_row = f"{rule['id']},S,{effect},{summary},{trigger}"
        elif "severity" in HEADER_TEMPLATE:
            s_row = f"{rule['id']},{rule['severity']},{effect},{summary}"
        elif INCLUDE_EXAMPLE:
            example = _example_for_rule(rule)
            s_row = f"{rule['id']},{effect},{summary},{example}"
        elif ",instruction}}" in HEADER_TEMPLATE and "effect" not in HEADER_TEMPLATE:
            # 2-column: embed effect in instruction
            s_row = f"{rule['id']},{effect}: {summary}"
        else:
            s_row = f"{rule['id']},{effect},{summary}"
        rows.append(s_row)

        if INCLUDE_DETAIL:
            # Only emit D rows for critical/high severity rules
            emit_detail = rule["severity"] in ("critical", "high")
            if emit_detail:
                if INCLUDE_EXAMPLE:
                    example = _example_for_rule(rule)
                    detail = f"BAD: {example}" if example else _truncate(
                        f"Ensure: {rule['description']}", DETAIL_MAX_WORDS)
                else:
                    detail = _truncate(
                        f"Ensure code does not violate: {rule['description']}",
                        DETAIL_MAX_WORDS,
                    )
                if INCLUDE_TRIGGER:
                    d_row = f"{rule['id']},D,{effect},{detail},{trigger}"
                else:
                    d_row = f"{rule['id']},D,{detail}"
                rows.append(d_row)

        if ROW_SEPARATOR:
            rows.append(ROW_SEPARATOR)

    # Strip trailing separator
    if ROW_SEPARATOR and rows and rows[-1] == ROW_SEPARATOR:
        rows.pop()

    parts = []
    if PREAMBLE:
        parts.append(PREAMBLE)

    if HEADER_TEMPLATE == "NUMBERED_LIST":
        # Numbered list format instead of TOON table
        for i, row in enumerate(rows, 1):
            parts.append(f"{i}. {row}")
    else:
        header = HEADER_TEMPLATE.format(count=len(rows))
        parts.append(header)
        parts.extend(rows)
    text = "\n".join(parts) + "\n"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    return out_path


# ---------------------------------------------------------------------------
# Claude invocation + compliance checking
# ---------------------------------------------------------------------------


def count_tokens(file_path: Path) -> int:
    """Count tokens in a file using tiktoken cl100k_base."""
    enc = tiktoken.get_encoding("cl100k_base")
    text = file_path.read_text()
    return len(enc.encode(text))


async def invoke_claude(task_prompt: str, rules_file: Path, model: str = "") -> str:
    """Invoke claude -p with rules file and return output."""
    cmd = [
        "claude",
        "-p",
        task_prompt,
        "--append-system-prompt-file",
        str(rules_file),
        "--output-format",
        "text",
    ]
    if model:
        cmd.extend(["--model", model])
    # Use sync subprocess.run in a thread to avoid hook backgrounding
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=300),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"claude exited {result.returncode}: {result.stderr[:500]}"
        )
    return result.stdout


def check_compliance(output: str, rules: list[dict[str, Any]]) -> dict[str, bool]:
    """Check each rule against output, return {rule_id: compliant}."""
    return {r["id"]: r["check"](output) for r in rules}


def compliance_rate(scores: dict[str, bool]) -> float:
    """Calculate compliance rate from scores dict."""
    if not scores:
        return 0.0
    return sum(scores.values()) / len(scores)


# ---------------------------------------------------------------------------
# A/B comparison
# ---------------------------------------------------------------------------


async def run_ab_task(
    task: dict[str, Any],
    rules: list[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    """Run a single task with both markdown and axiom rules."""
    task_dir = output_dir / task["id"]
    task_dir.mkdir(parents=True, exist_ok=True)

    # Generate both rule files
    md_file = write_markdown_rules(rules, task_dir / "rules.md")
    axiom_file = write_axiom_rules(rules, task_dir / "rules.axiom")

    md_tokens = count_tokens(md_file)
    axiom_tokens = count_tokens(axiom_file)

    # Run both invocations
    print(f"  [{task['id']}] invoking claude with markdown rules ({md_tokens} tokens)...")
    md_output = await invoke_claude(task["prompt"], md_file)
    (task_dir / "output_markdown.txt").write_text(md_output)

    print(f"  [{task['id']}] invoking claude with axiom rules ({axiom_tokens} tokens)...")
    axiom_output = await invoke_claude(task["prompt"], axiom_file)
    (task_dir / "output_axiom.txt").write_text(axiom_output)

    # Check compliance
    md_scores = check_compliance(md_output, rules)
    axiom_scores = check_compliance(axiom_output, rules)

    result = {
        "task": task["id"],
        "markdown": {
            "compliance_rate": compliance_rate(md_scores),
            "scores": md_scores,
            "tokens": md_tokens,
        },
        "axiom": {
            "compliance_rate": compliance_rate(axiom_scores),
            "scores": axiom_scores,
            "tokens": axiom_tokens,
        },
        "token_savings_pct": round(
            (1 - axiom_tokens / md_tokens) * 100, 1
        ) if md_tokens > 0 else 0.0,
    }

    return result


async def run_ab_comparison(
    task_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Run A/B comparison across all (or filtered) tasks."""
    output_dir = OUTPUT_DIR / f"ab_{int(time.time())}"
    output_dir.mkdir(parents=True, exist_ok=True)

    tasks = TASKS
    if task_filter:
        tasks = [t for t in TASKS if t["id"] == task_filter]
        if not tasks:
            print(f"ERROR: no task with id '{task_filter}'")
            sys.exit(1)

    results: list[dict[str, Any]] = []
    for task in tasks:
        print(f"\n--- Task: {task['id']} ---")
        result = await run_ab_task(task, COMPLIANCE_RULES, output_dir)
        results.append(result)

        md_rate = result["markdown"]["compliance_rate"]
        ax_rate = result["axiom"]["compliance_rate"]
        savings = result["token_savings_pct"]
        print(f"  markdown compliance: {md_rate:.0%}")
        print(f"  axiom compliance:    {ax_rate:.0%}")
        print(f"  token savings:       {savings:.1f}%")

    # Save combined results
    results_file = output_dir / "results.json"
    results_file.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved to {results_file}")

    # Print summary
    print("\n=== Summary ===")
    for r in results:
        delta = r["axiom"]["compliance_rate"] - r["markdown"]["compliance_rate"]
        sign = "+" if delta >= 0 else ""
        print(
            f"  {r['task']:20s}  md={r['markdown']['compliance_rate']:.0%}  "
            f"axiom={r['axiom']['compliance_rate']:.0%}  "
            f"delta={sign}{delta:.0%}  "
            f"tokens saved={r['token_savings_pct']:.1f}%"
        )

    return results


# ---------------------------------------------------------------------------
# Dry-run mode (no Claude invocation — validates rule checks + format gen)
# ---------------------------------------------------------------------------


def run_dry(task_filter: str | None = None) -> None:
    """Generate rule files and validate check functions without invoking Claude."""
    output_dir = OUTPUT_DIR / "dry"
    output_dir.mkdir(parents=True, exist_ok=True)

    tasks = TASKS
    if task_filter:
        tasks = [t for t in TASKS if t["id"] == task_filter]

    # Write both formats
    md_file = write_markdown_rules(COMPLIANCE_RULES, output_dir / "rules.md")
    axiom_file = write_axiom_rules(COMPLIANCE_RULES, output_dir / "rules.axiom")

    md_tokens = count_tokens(md_file)
    axiom_tokens = count_tokens(axiom_file)

    print(f"Markdown rules: {md_file} ({md_tokens} tokens)")
    print(f"Axiom rules:    {axiom_file} ({axiom_tokens} tokens)")
    print(f"Token savings:  {(1 - axiom_tokens / md_tokens) * 100:.1f}%")
    print(f"\nTasks: {[t['id'] for t in tasks]}")
    print(f"Rules: {[r['id'] for r in COMPLIANCE_RULES]}")

    # Validate check functions don't crash
    test_code = 'import logging\nprint("debug")\ndef fetch(url):\n    pass\n'
    print(f"\nValidating checks against sample violating code...")
    for rule in COMPLIANCE_RULES:
        try:
            result = rule["check"](test_code)
            status = "PASS" if result else "VIOLATION"
            print(f"  {rule['id']:20s} -> {status}")
        except Exception as e:
            print(f"  {rule['id']:20s} -> ERROR: {e}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Axiom compliance validation runner")
    parser.add_argument(
        "--mode",
        choices=["ab", "dry", "autoresearch"],
        default="dry",
        help="Run mode: ab (A/B comparison), dry (no Claude), autoresearch (tuning loop)",
    )
    parser.add_argument("--task", default=None, help="Filter to single task id")
    args = parser.parse_args()

    if args.mode == "dry":
        run_dry(args.task)
    elif args.mode == "ab":
        asyncio.run(run_ab_comparison(args.task))
    elif args.mode == "autoresearch":
        print(
            "Autoresearch mode is designed to be run by an AI agent.\n"
            "See program.md for the autonomous experiment protocol.\n"
            "To run manually: iterate on format.py, then run --mode ab."
        )
        sys.exit(0)


if __name__ == "__main__":
    main()
