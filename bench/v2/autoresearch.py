#!/usr/bin/env python3
"""AxiomBench v2 autoresearch — autonomous format tuning with real Claude calls.

Runs an iterative optimization loop:
1. Establish baseline compliance rate
2. Mutate format parameters
3. Run compliance tests
4. Keep improvements, discard regressions

Usage:
    python bench/v2/autoresearch.py --model sonnet --max-experiments 20
    python bench/v2/autoresearch.py --model opus --calls-per-experiment 5
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import sys
import time
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

from config import MODEL_IDS
from formats import (
    FORMAT_GENERATORS,
    _SEVERITY_TO_EFFECT,
    generate_toon_rules,
)
from rules import RULES, Rule
from runner import check_compliance, compliance_rate, invoke_claude
from tasks import TASKS, Task


def _log(msg: str) -> None:
    """Print progress to stderr."""
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Format parameter space
# ---------------------------------------------------------------------------

# Mutable parameters for TOON format tuning
_DEFAULT_PARAMS: dict = {
    "include_trigger": True,
    "include_severity": True,
    "sort_by_severity": True,
    "header_style": "toon",  # toon | numbered | flat
    "preamble": "",
    "effect_vocabulary": ["MUST_NOT", "MUST", "SHOULD", "INFO"],
}

# Mutation options
_PREAMBLE_OPTIONS = [
    "",
    "Follow all rules strictly.",
    "CRITICAL: Comply with every rule below. Violations are unacceptable.",
    "Rules for code generation:",
]

_HEADER_STYLES = ["toon", "numbered", "flat"]


def mutate_params(params: dict) -> dict:
    """Apply a random mutation to format parameters."""
    p = copy.deepcopy(params)
    mutation = random.choice([
        "toggle_trigger",
        "toggle_severity",
        "toggle_sort",
        "change_header",
        "change_preamble",
        "change_effects",
    ])

    if mutation == "toggle_trigger":
        p["include_trigger"] = not p["include_trigger"]
    elif mutation == "toggle_severity":
        p["include_severity"] = not p["include_severity"]
    elif mutation == "toggle_sort":
        p["sort_by_severity"] = not p["sort_by_severity"]
    elif mutation == "change_header":
        p["header_style"] = random.choice(_HEADER_STYLES)
    elif mutation == "change_preamble":
        p["preamble"] = random.choice(_PREAMBLE_OPTIONS)
    elif mutation == "change_effects":
        # Randomly simplify or expand effect vocabulary
        options = [
            ["MUST_NOT", "MUST", "SHOULD", "INFO"],
            ["MUST_NOT", "MUST"],
            ["NO", "YES", "PREFER"],
            ["BLOCK", "REQUIRE", "SUGGEST"],
        ]
        p["effect_vocabulary"] = random.choice(options)

    return p


def render_toon_with_params(rules: list[Rule], params: dict) -> str:
    """Render TOON rules using given parameters."""
    severity_order = ["critical", "high", "medium", "low"]
    sorted_rules = (
        sorted(rules, key=lambda r: severity_order.index(r.severity))
        if params["sort_by_severity"]
        else list(rules)
    )

    effect_map = {
        "critical": params["effect_vocabulary"][0] if len(params["effect_vocabulary"]) > 0 else "MUST_NOT",
        "high": params["effect_vocabulary"][0] if len(params["effect_vocabulary"]) > 0 else "MUST_NOT",
        "medium": params["effect_vocabulary"][1] if len(params["effect_vocabulary"]) > 1 else "MUST",
        "low": params["effect_vocabulary"][2] if len(params["effect_vocabulary"]) > 2 else "SHOULD",
    }

    rows: list[str] = []
    for rule in sorted_rules:
        effect = effect_map.get(rule.severity, "INFO")
        parts = [rule.id]
        if params["include_severity"]:
            parts.append(rule.severity)
        parts.append(effect)
        parts.append(rule.description)
        if params["include_trigger"]:
            parts.append(rule.trigger)
        rows.append(",".join(parts))

    # Header
    cols = ["id"]
    if params["include_severity"]:
        cols.append("level")
    cols.extend(["effect", "instruction"])
    if params["include_trigger"]:
        cols.append("trigger")

    lines: list[str] = []
    if params["preamble"]:
        lines.append(params["preamble"])

    if params["header_style"] == "toon":
        header = f"RULES[{len(rows)}]{{{','.join(cols)}}}:"
        lines.append(header)
        lines.extend(rows)
    elif params["header_style"] == "numbered":
        for i, row in enumerate(rows, 1):
            lines.append(f"{i}. {row}")
    else:  # flat
        lines.extend(rows)

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Experiment loop
# ---------------------------------------------------------------------------


def evaluate_format(
    rules_text: str,
    tasks: list[Task],
    rules: list[Rule],
    model: str,
    n_calls: int,
) -> tuple[float, float]:
    """Run n_calls compliance tests and return (mean_rate, token_count).

    Samples tasks randomly for each call.
    """
    rates: list[float] = []
    for i in range(n_calls):
        task = random.choice(tasks)
        try:
            output, _ = invoke_claude(task.prompt, rules_text, model)
            scores = check_compliance(output, rules)
            rate = compliance_rate(scores)
            rates.append(rate)
        except Exception as e:
            _log(f"  Call {i+1} failed: {e}")
            rates.append(0.0)

    mean_rate = sum(rates) / len(rates) if rates else 0.0
    token_count = len(rules_text.split())  # rough word count
    return mean_rate, token_count


def run_autoresearch(
    tasks: list[Task],
    rules: list[Rule],
    model: str = "sonnet",
    max_experiments: int = 20,
    calls_per_experiment: int = 5,
    output_dir: Path | None = None,
) -> None:
    """Autonomous format tuning with real Claude calls."""
    if output_dir is None:
        output_dir = Path(__file__).parent / "results" / f"autoresearch_{int(time.time())}"
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "experiments.jsonl"

    _log(f"Autoresearch: model={model}, max_experiments={max_experiments}, "
         f"calls_per_experiment={calls_per_experiment}")
    _log(f"Output: {output_dir}")

    # Step 1: Baseline with default TOON
    _log("\n--- Establishing baseline ---")
    baseline_text = generate_toon_rules(rules)
    baseline_rate, baseline_tokens = evaluate_format(
        baseline_text, tasks, rules, model, calls_per_experiment
    )
    _log(f"Baseline: compliance={baseline_rate:.1%}, tokens={baseline_tokens}")

    best_params = copy.deepcopy(_DEFAULT_PARAMS)
    best_rate = baseline_rate
    best_tokens = baseline_tokens

    # Log baseline
    with open(log_path, "a") as f:
        f.write(json.dumps({
            "experiment": 0,
            "type": "baseline",
            "params": best_params,
            "compliance_rate": round(best_rate, 4),
            "tokens": best_tokens,
            "accepted": True,
            "timestamp": time.time(),
        }) + "\n")

    # Step 2: Iterative tuning
    for exp in range(1, max_experiments + 1):
        _log(f"\n--- Experiment {exp}/{max_experiments} ---")

        # Mutate
        candidate_params = mutate_params(best_params)
        candidate_text = render_toon_with_params(rules, candidate_params)
        _log(f"  Mutation: {_describe_diff(best_params, candidate_params)}")

        # Evaluate
        candidate_rate, candidate_tokens = evaluate_format(
            candidate_text, tasks, rules, model, calls_per_experiment
        )
        _log(f"  Result: compliance={candidate_rate:.1%}, tokens={candidate_tokens}")

        # Accept/reject
        accepted = False
        reason = ""
        if candidate_rate > best_rate + 0.01:
            accepted = True
            reason = f"compliance improved ({best_rate:.1%} -> {candidate_rate:.1%})"
        elif abs(candidate_rate - best_rate) <= 0.01 and candidate_tokens < best_tokens:
            accepted = True
            reason = f"same compliance, fewer tokens ({best_tokens} -> {candidate_tokens})"
        else:
            reason = f"no improvement (rate={candidate_rate:.1%} vs {best_rate:.1%})"

        if accepted:
            _log(f"  ACCEPTED: {reason}")
            best_params = candidate_params
            best_rate = candidate_rate
            best_tokens = candidate_tokens
        else:
            _log(f"  REJECTED: {reason}")

        # Log
        with open(log_path, "a") as f:
            f.write(json.dumps({
                "experiment": exp,
                "type": "mutation",
                "params": candidate_params,
                "compliance_rate": round(candidate_rate, 4),
                "tokens": candidate_tokens,
                "accepted": accepted,
                "reason": reason,
                "timestamp": time.time(),
            }) + "\n")

    # Summary
    _log(f"\n{'=' * 50}")
    _log(f"Autoresearch complete.")
    _log(f"Best compliance: {best_rate:.1%} (baseline: {baseline_rate:.1%})")
    _log(f"Best tokens: {best_tokens} (baseline: {baseline_tokens})")
    _log(f"Best params: {json.dumps(best_params, indent=2)}")
    _log(f"Log: {log_path}")

    # Save best format
    best_text = render_toon_with_params(rules, best_params)
    (output_dir / "best_format.txt").write_text(best_text)
    (output_dir / "best_params.json").write_text(json.dumps(best_params, indent=2))


def _describe_diff(old: dict, new: dict) -> str:
    """Describe what changed between two param dicts."""
    diffs = []
    for k in new:
        if old.get(k) != new.get(k):
            diffs.append(f"{k}: {old.get(k)} -> {new.get(k)}")
    return "; ".join(diffs) if diffs else "no change"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AxiomBench v2 autoresearch -- autonomous format tuning"
    )
    parser.add_argument(
        "--model",
        choices=["sonnet", "opus"],
        default="sonnet",
        help="Model to use (default: sonnet)",
    )
    parser.add_argument(
        "--max-experiments",
        type=int,
        default=20,
        help="Maximum tuning iterations (default: 20)",
    )
    parser.add_argument(
        "--calls-per-experiment",
        type=int,
        default=5,
        help="Claude calls per experiment (default: 5)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else None

    run_autoresearch(
        tasks=TASKS,
        rules=RULES,
        model=args.model,
        max_experiments=args.max_experiments,
        calls_per_experiment=args.calls_per_experiment,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
