#!/usr/bin/env python3
"""AxiomBench v2 — statistically rigorous compliance benchmark runner.

Usage:
    python bench/v2/runner.py --phase quick
    python bench/v2/runner.py --phase baseline --model sonnet --runs 4
    python bench/v2/runner.py --phase final --runs 5
    python bench/v2/runner.py --phase overnight
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Ensure script directory is importable
_script_dir = Path(__file__).resolve().parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

from config import CALL_TIMEOUT, CLAUDE_BIN, CLEAN_PATH, MODEL_IDS, PHASES, VLLM_ENDPOINT
from formats import generate_rules
from rules import RULES, Rule
from tasks import TASKS, Task


def _log(msg: str) -> None:
    """Print progress to stderr."""
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Claude invocation
# ---------------------------------------------------------------------------


def invoke_claude(prompt: str, rules_text: str, model: str = "sonnet") -> tuple[str, float]:
    """Invoke claude -p with rules as --append-system-prompt-file.

    Returns (output_text, elapsed_seconds).
    Uses subprocess.run (sync) with full claude path and clean PATH.
    """
    model_id = MODEL_IDS.get(model, model)

    # Write rules to temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="axiom_rules_"
    ) as f:
        f.write(rules_text)
        rules_file = f.name

    try:
        cmd = [
            CLAUDE_BIN,
            "-p",
            prompt,
            "--append-system-prompt-file",
            rules_file,
            "--output-format",
            "text",
            "--model",
            model_id,
        ]

        env = os.environ.copy()
        env["PATH"] = CLEAN_PATH

        t0 = time.monotonic()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=CALL_TIMEOUT,
            env=env,
        )
        elapsed = time.monotonic() - t0

        if result.returncode != 0:
            raise RuntimeError(
                f"claude exited {result.returncode}: {result.stderr[:500]}"
            )
        return result.stdout, elapsed
    finally:
        os.unlink(rules_file)


# ---------------------------------------------------------------------------
# Hermes/vLLM invocation
# ---------------------------------------------------------------------------


def strip_think_tags(text: str) -> str:
    """Strip <think>...</think> reasoning blocks from qwen3-coder output."""
    import re

    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def invoke_hermes(prompt: str, rules_text: str) -> tuple[str, float]:
    """Invoke vLLM directly via OpenAI-compatible API.

    Uses /v1/chat/completions endpoint. No subprocess, no CLI.
    Rules injected as system message. Think tags stripped from output.
    """
    import urllib.request

    url = f"{VLLM_ENDPOINT}/v1/chat/completions"
    payload = {
        "model": "qwen3-coder",
        "messages": [
            {"role": "system", "content": rules_text},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=CALL_TIMEOUT) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    elapsed = time.monotonic() - t0

    output = body["choices"][0]["message"]["content"]
    output = strip_think_tags(output)
    return output, elapsed


# ---------------------------------------------------------------------------
# Compliance checking
# ---------------------------------------------------------------------------


def check_compliance(output: str, rules: list[Rule]) -> dict[str, bool]:
    """Check each rule against output, return {rule_id: compliant}."""
    return {r.id: r.check(output) for r in rules}


def compliance_rate(scores: dict[str, bool]) -> float:
    """Calculate compliance rate from scores dict."""
    if not scores:
        return 0.0
    return sum(scores.values()) / len(scores)


# ---------------------------------------------------------------------------
# Result persistence (JSONL with resume support)
# ---------------------------------------------------------------------------


def _results_path(output_dir: Path) -> Path:
    """Path to the JSONL results file."""
    return output_dir / "results.jsonl"


def load_completed(output_dir: Path) -> set[tuple[str, str, str, int]]:
    """Load successfully-completed (task, format, model, run) tuples.

    Skips error entries so they get retried on resume.
    """
    path = _results_path(output_dir)
    completed: set[tuple[str, str, str, int]] = set()
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                try:
                    rec = json.loads(line)
                    if rec.get("status") == "error":
                        continue  # retry errors on resume
                    completed.add((
                        rec["task"],
                        rec["format"],
                        rec["model"],
                        rec["run"],
                    ))
                except (json.JSONDecodeError, KeyError):
                    continue
    return completed


def save_result(output_dir: Path, record: dict) -> None:
    """Append a single result record to the JSONL file."""
    path = _results_path(output_dir)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------


def run_experiment(
    tasks: list[Task],
    rules: list[Rule],
    formats: list[str],
    models: list[str],
    runs_per_cell: int,
    output_dir: Path,
) -> list[dict]:
    """Run full factorial experiment with incremental save and resume.

    Iterates over (task x format x model x run), skipping already-completed
    cells found in the JSONL results file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    completed = load_completed(output_dir)
    total_cells = len(tasks) * len(formats) * len(models) * runs_per_cell
    done_count = len(completed)

    _log(f"Experiment: {total_cells} total cells, {done_count} already done, "
         f"{total_cells - done_count} remaining")

    results: list[dict] = []
    cell_num = done_count
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 3  # stop after 3 consecutive failures (quota exhausted)

    for task in tasks:
        for fmt in formats:
            # Generate rules text once per format
            rules_text = generate_rules(fmt, rules)
            rules_tokens = len(rules_text.split())  # rough word count

            for model in models:
                for run in range(1, runs_per_cell + 1):
                    key = (task.id, fmt, model, run)
                    if key in completed:
                        continue

                    cell_num += 1
                    _log(
                        f"[{cell_num}/{total_cells}] "
                        f"task={task.id} format={fmt} model={model} run={run}"
                    )

                    try:
                        if model == "hermes":
                            output, elapsed = invoke_hermes(task.prompt, rules_text)
                        else:
                            output, elapsed = invoke_claude(task.prompt, rules_text, model)
                        scores = check_compliance(output, rules)
                        rate = compliance_rate(scores)
                        status = "ok"
                        error = ""
                        consecutive_errors = 0  # reset on success
                    except Exception as e:
                        output = ""
                        elapsed = 0.0
                        scores = {r.id: False for r in rules}
                        rate = 0.0
                        status = "error"
                        error = str(e)[:500]
                        consecutive_errors += 1
                        _log(f"  ERROR ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}): {error}")
                        if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                            _log(f"\n*** STOPPING: {MAX_CONSECUTIVE_ERRORS} consecutive errors — likely quota exhausted ***")
                            _log(f"*** Resume later with same command (will pick up where it left off) ***")
                            save_result(output_dir, {
                                "task": task.id, "format": fmt, "model": model, "run": run,
                                "status": "error", "compliance_rate": 0.0, "scores": scores,
                                "rules_tokens_approx": rules_tokens, "elapsed_seconds": 0.0,
                                "timestamp": time.time(), "error": error,
                            })
                            return results

                    record = {
                        "task": task.id,
                        "format": fmt,
                        "model": model,
                        "run": run,
                        "status": status,
                        "compliance_rate": round(rate, 4),
                        "scores": scores,
                        "rules_tokens_approx": rules_tokens,
                        "elapsed_seconds": round(elapsed, 2),
                        "timestamp": time.time(),
                        "error": error,
                    }

                    # Save output text to separate file for analysis
                    if output:
                        out_file = output_dir / f"{task.id}_{fmt}_{model}_r{run}.txt"
                        out_file.write_text(output)

                    save_result(output_dir, record)
                    results.append(record)

                    _log(f"  compliance={rate:.0%} elapsed={elapsed:.1f}s")

    _log(f"\nExperiment complete. {len(results)} new results saved to {_results_path(output_dir)}")
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AxiomBench v2 -- statistically rigorous compliance benchmark"
    )
    parser.add_argument(
        "--phase",
        choices=list(PHASES.keys()),
        default="quick",
        help="Experiment phase (default: quick)",
    )
    parser.add_argument(
        "--model",
        choices=["sonnet", "opus", "hermes"],
        default=None,
        help="Override model (default: use phase definition)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=None,
        help="Override runs per cell (default: use phase definition)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: bench/v2/results/<phase>_<timestamp>)",
    )
    parser.add_argument(
        "--formats",
        type=str,
        default=None,
        help="Comma-separated formats to test (default: markdown,toon,cacp)",
    )
    parser.add_argument(
        "--task",
        type=str,
        default=None,
        help="Filter to single task id",
    )

    args = parser.parse_args()

    phase = PHASES[args.phase]
    models = [args.model] if args.model else phase["models"]
    runs = args.runs if args.runs is not None else phase["runs"]
    formats = args.formats.split(",") if args.formats else ["markdown", "toon", "cacp"]
    tasks = TASKS
    if args.task:
        tasks = [t for t in TASKS if t.id == args.task]
        if not tasks:
            _log(f"ERROR: no task with id '{args.task}'")
            sys.exit(1)

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = (
            Path(__file__).parent / "results" / f"{args.phase}_{int(time.time())}"
        )

    total = len(tasks) * len(formats) * len(models) * runs
    est_minutes = total * 0.75  # ~45s average per call
    _log(f"Phase: {args.phase} ({phase['description']})")
    _log(f"Models: {models}, Runs: {runs}, Formats: {formats}")
    _log(f"Total calls: {total}, Estimated time: ~{est_minutes:.0f} min")
    _log(f"Output: {output_dir}")
    _log("")

    run_experiment(
        tasks=tasks,
        rules=RULES,
        formats=formats,
        models=models,
        runs_per_cell=runs,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
