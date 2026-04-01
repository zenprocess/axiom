# PostToolUse Compliance Hook

How to achieve near-100% rule compliance using a three-layer architecture.

## Architecture

```
Layer 1: Static Format (Axiom compiled rules in system prompt)
  |  ~91% compliance baseline
  v
Layer 2: Dynamic Hook (PostToolUse compliance checker)
  |  Catches remaining ~9% in-flight, before agent continues
  v
Layer 3: Pre-Merge Gate (CI / pre-commit validation)
  |  Final safety net before code reaches main
  v
~100% compliance
```

**Layer 1** sets the floor. Axiom rules prime the model with compressed, attention-optimized instructions. This alone achieves ~91% compliance -- the same as verbose markdown.

**Layer 2** catches violations as they happen. After each file write or edit, the hook inspects the affected file and injects a correction prompt if rules are violated. The agent fixes the violation before continuing.

**Layer 3** is defense in depth. A CI check or pre-commit hook validates all modified files against the rule set before merge.

## Claude Code Configuration

Add a PostToolUse hook in your Claude Code `settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "write_to_file|edit_file|create_file",
        "command": "python /path/to/compliance_checker.py $TOOL_INPUT_FILE",
        "description": "Check compliance rules after file writes"
      }
    ]
  }
}
```

The hook receives the tool input (including the file path and content) via `$TOOL_INPUT_FILE`. It should:

1. Parse the affected file path from the tool input
2. Read the file content
3. Run all compliance rules against the content
4. If violations found: print a structured correction to stdout (this gets injected into the agent's context)
5. If no violations: exit silently (empty stdout = no injection)

### Correction Format

When violations are detected, the hook outputs a structured correction:

```
COMPLIANCE_VIOLATION: {rule_id}
FILE: {file_path}
DESCRIPTION: {rule description}
FIX: {specific instruction to fix the violation}
```

Multiple violations produce multiple blocks. The agent receives these as context and fixes them before proceeding.

### Example Hook Script

```python
#!/usr/bin/env python3
"""PostToolUse compliance checker for Claude Code hooks."""

import json
import sys
from pathlib import Path

# Import rules from the Axiom benchmark
from bench.rules import COMPLIANCE_RULES


def check_file(file_path: str) -> list[dict]:
    """Check a file against all compliance rules."""
    content = Path(file_path).read_text()
    violations = []
    for rule in COMPLIANCE_RULES:
        if not rule["check"](content):
            violations.append(rule)
    return violations


def main() -> None:
    """Read tool input, check compliance, emit corrections."""
    tool_input_file = sys.argv[1]
    tool_input = json.loads(Path(tool_input_file).read_text())

    # Extract file path from tool input
    file_path = tool_input.get("path") or tool_input.get("file_path")
    if not file_path or not Path(file_path).exists():
        return

    # Only check Python files
    if not file_path.endswith(".py"):
        return

    violations = check_file(file_path)
    for v in violations:
        print(f"COMPLIANCE_VIOLATION: {v['id']}")
        print(f"FILE: {file_path}")
        print(f"DESCRIPTION: {v['description']}")
        print(f"FIX: Modify the code to comply with: {v['description']}")
        print()


if __name__ == "__main__":
    main()
```

## Switchyard / Hermes Integration

For multi-agent dispatch systems using [Switchyard](https://github.com/zenprocess/switchyard), the compliance hook integrates at the Hermes engine level:

1. **Hermes PostToolUse**: After each tool call in the Hermes tool-calling loop, run compliance checks on any files written. Inject correction into the next turn's messages if violations are found.

2. **Response Gate**: Switchyard's response gate already validates CACP responses. Add compliance checking as a gate criterion: if the final worktree contains files violating critical rules, demote the dispatch result.

3. **Telemetry**: Record compliance scores in dispatch telemetry for SLI monitoring. Track per-rule violation rates to identify rules that need stronger enforcement.

## Sieeve ComplianceChecker

The compliance checking logic originates from [Sieeve](https://github.com/zenprocess/sieeve)'s `scripts/compliance/` module. The same `rules.py` and check functions are used in:

- The Axiom benchmark (`bench/rules.py`)
- The PostToolUse hook (runtime enforcement)
- CI validation (pre-merge gate)

This ensures consistency: the same rules, the same checks, across all three layers.
