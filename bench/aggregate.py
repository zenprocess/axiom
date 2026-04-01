#!/usr/bin/env python3
"""Aggregate compliance results from all A/B runs.

Reads all JSON result files from bench/results/ and computes:
- Per-task averages for markdown and axiom
- Overall averages
- Win/loss/tie counts
- Token savings

Usage:
    python bench/aggregate.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


RESULTS_DIR = Path(__file__).parent / "results"


def load_all_results() -> list[dict]:
    """Load all result JSON files and normalize to a common format."""
    records: list[dict] = []

    for path in sorted(RESULTS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        for entry in data:
            task = entry.get("task", "unknown")

            # Handle both formats: full_run (md/axiom keys) and ab_* (markdown/axiom dicts)
            if "markdown" in entry and isinstance(entry["markdown"], dict):
                md_rate = entry["markdown"]["compliance_rate"]
                ax_rate = entry["axiom"]["compliance_rate"]
                md_tokens = entry["markdown"].get("tokens", 0)
                ax_tokens = entry["axiom"].get("tokens", 0)
            elif "md" in entry:
                md_rate = entry["md"]
                ax_rate = entry["axiom"]
                md_tokens = 0
                ax_tokens = 0
            else:
                continue

            records.append({
                "source": path.stem,
                "task": task,
                "md_rate": md_rate,
                "ax_rate": ax_rate,
                "md_tokens": md_tokens,
                "ax_tokens": ax_tokens,
            })

    return records


def aggregate(records: list[dict]) -> None:
    """Compute and print aggregate statistics."""
    if not records:
        print("No results found.")
        return

    # Per-task aggregation
    task_md: dict[str, list[float]] = defaultdict(list)
    task_ax: dict[str, list[float]] = defaultdict(list)

    for r in records:
        task_md[r["task"]].append(r["md_rate"])
        task_ax[r["task"]].append(r["ax_rate"])

    print("Per-task averages:")
    print(f"  {'Task':<20s} {'Runs':>5s} {'Markdown':>10s} {'Axiom':>10s} {'Winner':<12s}")
    print(f"  {'----':<20s} {'----':>5s} {'--------':>10s} {'-----':>10s} {'------':<12s}")

    total_md = []
    total_ax = []
    wins = losses = ties = 0

    for task in sorted(task_md.keys()):
        md_vals = task_md[task]
        ax_vals = task_ax[task]
        md_avg = sum(md_vals) / len(md_vals)
        ax_avg = sum(ax_vals) / len(ax_vals)
        total_md.extend(md_vals)
        total_ax.extend(ax_vals)

        if abs(md_avg - ax_avg) < 0.01:
            winner = "Tie"
            ties += len(md_vals)
        elif ax_avg > md_avg:
            winner = "Axiom"
            wins += len(md_vals)
        else:
            winner = "Markdown"
            losses += len(md_vals)

        print(
            f"  {task:<20s} {len(md_vals):>5d} "
            f"{md_avg:>9.1%} {ax_avg:>9.1%} {winner:<12s}"
        )

    # Overall
    overall_md = sum(total_md) / len(total_md) if total_md else 0
    overall_ax = sum(total_ax) / len(total_ax) if total_ax else 0

    print(f"\nOverall ({len(total_md)} runs):")
    print(f"  Markdown mean compliance: {overall_md:.1%}")
    print(f"  Axiom mean compliance:    {overall_ax:.1%}")
    print(f"  Wins / Losses / Ties:     {wins} / {losses} / {ties}")

    # Token info from runs that have it
    token_records = [r for r in records if r["md_tokens"] > 0]
    if token_records:
        md_tok = token_records[0]["md_tokens"]
        ax_tok = token_records[0]["ax_tokens"]
        savings = (1 - ax_tok / md_tok) * 100 if md_tok > 0 else 0
        print(f"\n  Markdown tokens: {md_tok}")
        print(f"  Axiom tokens:    {ax_tok}")
        print(f"  Token savings:   {savings:.1f}%")


if __name__ == "__main__":
    records = load_all_results()
    aggregate(records)
