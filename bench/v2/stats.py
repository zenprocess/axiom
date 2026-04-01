#!/usr/bin/env python3
"""Statistical analysis for AxiomBench v2 results.

Usage:
    python bench/v2/stats.py bench/v2/results/
    python bench/v2/stats.py bench/v2/results/final_1234567890/
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

try:
    from scipy import stats as sp_stats

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


@dataclass
class CellStats:
    """Statistics for a single (format, model) or (format, model, task) cell."""

    mean: float = 0.0
    std: float = 0.0
    ci_low: float = 0.0
    ci_high: float = 0.0
    n: int = 0
    values: list[float] = field(default_factory=list)


@dataclass
class ComparisonResult:
    """Result of a statistical comparison between two formats."""

    format_a: str = ""
    format_b: str = ""
    wilcoxon_stat: float | None = None
    wilcoxon_p: float | None = None
    cohens_d: float | None = None
    tost_p: float | None = None
    equivalent: bool | None = None  # |diff| < 5%?
    mean_diff: float = 0.0


@dataclass
class AnalysisReport:
    """Complete analysis output."""

    # Table 1: Per format x model
    format_model_stats: dict[str, dict[str, CellStats]] = field(default_factory=dict)
    # Table 2: Per task breakdown
    task_stats: dict[str, dict[str, CellStats]] = field(default_factory=dict)
    # Table 3: Per rule violation rates
    rule_violations: dict[str, dict[str, float]] = field(default_factory=dict)
    # Statistical comparisons
    comparisons: list[ComparisonResult] = field(default_factory=list)
    # Token savings
    token_savings: dict[str, float] = field(default_factory=dict)
    # Raw records
    n_records: int = 0


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_results(results_path: Path) -> list[dict]:
    """Load results from JSONL file(s) in a directory or single file."""
    records: list[dict] = []

    if results_path.is_file() and results_path.suffix == ".jsonl":
        files = [results_path]
    elif results_path.is_dir():
        files = sorted(results_path.rglob("results.jsonl"))
    else:
        print(f"ERROR: {results_path} is not a JSONL file or directory", file=sys.stderr)
        sys.exit(1)

    for f in files:
        for line in f.read_text().splitlines():
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    return records


# ---------------------------------------------------------------------------
# Bootstrap CI
# ---------------------------------------------------------------------------


def bootstrap_ci(
    values: list[float], n_resamples: int = 1000, ci: float = 0.95
) -> tuple[float, float]:
    """Compute bootstrap confidence interval."""
    if len(values) < 2:
        return (values[0] if values else 0.0, values[0] if values else 0.0)

    arr = np.array(values)
    rng = np.random.default_rng(42)
    boot_means = np.array([
        rng.choice(arr, size=len(arr), replace=True).mean()
        for _ in range(n_resamples)
    ])
    alpha = (1 - ci) / 2
    return float(np.quantile(boot_means, alpha)), float(np.quantile(boot_means, 1 - alpha))


# ---------------------------------------------------------------------------
# Effect size
# ---------------------------------------------------------------------------


def cohens_d(a: list[float], b: list[float]) -> float:
    """Compute Cohen's d effect size."""
    a_arr, b_arr = np.array(a), np.array(b)
    n_a, n_b = len(a_arr), len(b_arr)
    if n_a < 2 or n_b < 2:
        return 0.0
    pooled_std = np.sqrt(
        ((n_a - 1) * a_arr.std(ddof=1) ** 2 + (n_b - 1) * b_arr.std(ddof=1) ** 2)
        / (n_a + n_b - 2)
    )
    if pooled_std == 0:
        return 0.0
    return float((a_arr.mean() - b_arr.mean()) / pooled_std)


# ---------------------------------------------------------------------------
# TOST equivalence test
# ---------------------------------------------------------------------------


def tost_test(
    a: list[float], b: list[float], margin: float = 0.05
) -> tuple[float | None, bool]:
    """Two one-sided t-tests for equivalence within margin.

    Returns (max_p_value, is_equivalent).
    """
    if not HAS_SCIPY or len(a) < 2 or len(b) < 2:
        return None, False

    a_arr, b_arr = np.array(a), np.array(b)
    diff = a_arr.mean() - b_arr.mean()
    se = np.sqrt(a_arr.var(ddof=1) / len(a_arr) + b_arr.var(ddof=1) / len(b_arr))

    if se == 0:
        return (0.0, abs(diff) < margin)

    df = len(a_arr) + len(b_arr) - 2

    # Test 1: diff > -margin (i.e., diff + margin > 0)
    t1 = (diff + margin) / se
    p1 = 1 - sp_stats.t.cdf(t1, df)

    # Test 2: diff < margin (i.e., margin - diff > 0)
    t2 = (margin - diff) / se
    p2 = 1 - sp_stats.t.cdf(t2, df)

    max_p = max(p1, p2)
    return float(max_p), max_p < 0.05


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------


def analyze(results_path: Path) -> AnalysisReport:
    """Compute all statistics from raw results."""
    records = load_results(results_path)
    if not records:
        print("No results found.", file=sys.stderr)
        return AnalysisReport()

    report = AnalysisReport(n_records=len(records))

    # Group by (format, model)
    fmt_model: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    # Group by (task, format+model key)
    task_group: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    # Per-rule violations by format
    rule_fmt_violations: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    rule_fmt_total: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    # Token counts by format
    token_counts: dict[str, list[int]] = defaultdict(list)

    for rec in records:
        fmt = rec["format"]
        model = rec["model"]
        task = rec["task"]
        rate = rec["compliance_rate"]

        fmt_model[fmt][model].append(rate)
        task_group[task][f"{fmt}/{model}"].append(rate)
        token_counts[fmt].append(rec.get("rules_tokens_approx", 0))

        scores = rec.get("scores", {})
        for rule_id, passed in scores.items():
            rule_fmt_total[rule_id][fmt] += 1
            if not passed:
                rule_fmt_violations[rule_id][fmt] += 1

    # Table 1: Format x Model stats
    for fmt, model_data in sorted(fmt_model.items()):
        report.format_model_stats[fmt] = {}
        for model, values in sorted(model_data.items()):
            ci_low, ci_high = bootstrap_ci(values)
            report.format_model_stats[fmt][model] = CellStats(
                mean=float(np.mean(values)),
                std=float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                ci_low=ci_low,
                ci_high=ci_high,
                n=len(values),
                values=values,
            )

    # Table 2: Per-task breakdown
    for task, group_data in sorted(task_group.items()):
        report.task_stats[task] = {}
        for key, values in sorted(group_data.items()):
            ci_low, ci_high = bootstrap_ci(values)
            report.task_stats[task][key] = CellStats(
                mean=float(np.mean(values)),
                std=float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                ci_low=ci_low,
                ci_high=ci_high,
                n=len(values),
                values=values,
            )

    # Table 3: Per-rule violation rates by format
    for rule_id in sorted(rule_fmt_total.keys()):
        report.rule_violations[rule_id] = {}
        for fmt in sorted(rule_fmt_total[rule_id].keys()):
            total = rule_fmt_total[rule_id][fmt]
            violations = rule_fmt_violations[rule_id].get(fmt, 0)
            report.rule_violations[rule_id][fmt] = violations / total if total > 0 else 0.0

    # Statistical comparisons: TOON vs markdown, CACP vs markdown (per model)
    for model in set(m for fdata in fmt_model.values() for m in fdata):
        md_values = fmt_model.get("markdown", {}).get(model, [])
        for alt_fmt in ["toon", "cacp"]:
            alt_values = fmt_model.get(alt_fmt, {}).get(model, [])
            if not md_values or not alt_values:
                continue

            comp = ComparisonResult(
                format_a=alt_fmt,
                format_b="markdown",
                mean_diff=float(np.mean(alt_values) - np.mean(md_values)),
                cohens_d=cohens_d(alt_values, md_values),
            )

            # Wilcoxon signed-rank (paired by task — aggregate per-task means)
            if HAS_SCIPY and len(md_values) >= 5 and len(alt_values) >= 5:
                # Pair by position (run order)
                min_len = min(len(md_values), len(alt_values))
                try:
                    stat, p = sp_stats.wilcoxon(
                        alt_values[:min_len], md_values[:min_len]
                    )
                    comp.wilcoxon_stat = float(stat)
                    comp.wilcoxon_p = float(p)
                except ValueError:
                    pass  # all differences zero

            # TOST equivalence
            tost_p, equiv = tost_test(alt_values, md_values, margin=0.05)
            comp.tost_p = tost_p
            comp.equivalent = equiv

            report.comparisons.append(comp)

    # Token savings
    md_tokens = token_counts.get("markdown", [])
    if md_tokens:
        md_mean = np.mean(md_tokens)
        for fmt in ["toon", "cacp"]:
            fmt_tokens = token_counts.get(fmt, [])
            if fmt_tokens and md_mean > 0:
                report.token_savings[fmt] = float(
                    (1 - np.mean(fmt_tokens) / md_mean) * 100
                )

    return report


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------


def print_report(report: AnalysisReport) -> None:
    """Print analysis to stdout."""
    print(f"\n{'=' * 70}")
    print(f"AxiomBench v2 Analysis  ({report.n_records} records)")
    print(f"{'=' * 70}")

    # Table 1
    print(f"\n--- Table 1: Compliance Rate by Format x Model ---\n")
    print(f"{'Format':<12s} {'Model':<8s} {'Mean':>8s} {'Std':>8s} {'95% CI':>16s} {'N':>5s}")
    print(f"{'------':<12s} {'-----':<8s} {'----':>8s} {'---':>8s} {'------':>16s} {'-':>5s}")
    for fmt, model_data in sorted(report.format_model_stats.items()):
        for model, cell in sorted(model_data.items()):
            ci_str = f"[{cell.ci_low:.3f}, {cell.ci_high:.3f}]"
            print(
                f"{fmt:<12s} {model:<8s} {cell.mean:>8.3f} {cell.std:>8.3f} "
                f"{ci_str:>16s} {cell.n:>5d}"
            )

    # Table 2
    print(f"\n--- Table 2: Per-Task Breakdown ---\n")
    all_keys = sorted(set(
        k for tdata in report.task_stats.values() for k in tdata
    ))
    header = f"{'Task':<18s}" + "".join(f" {k:>14s}" for k in all_keys)
    print(header)
    print("-" * len(header))
    for task, tdata in sorted(report.task_stats.items()):
        row = f"{task:<18s}"
        for k in all_keys:
            if k in tdata:
                row += f" {tdata[k].mean:>14.3f}"
            else:
                row += f" {'--':>14s}"
        print(row)

    # Table 3
    print(f"\n--- Table 3: Per-Rule Violation Rate by Format ---\n")
    all_fmts = sorted(set(
        f for rdata in report.rule_violations.values() for f in rdata
    ))
    header = f"{'Rule':<20s}" + "".join(f" {f:>10s}" for f in all_fmts)
    print(header)
    print("-" * len(header))
    for rule_id, rdata in sorted(report.rule_violations.items()):
        row = f"{rule_id:<20s}"
        for f in all_fmts:
            rate = rdata.get(f, 0.0)
            row += f" {rate:>9.1%}"
        print(row)

    # Comparisons
    if report.comparisons:
        print(f"\n--- Statistical Comparisons (vs markdown) ---\n")
        for comp in report.comparisons:
            print(f"{comp.format_a} vs {comp.format_b}:")
            print(f"  Mean difference: {comp.mean_diff:+.4f}")
            print(f"  Cohen's d:       {comp.cohens_d:+.4f}")
            if comp.wilcoxon_p is not None:
                sig = "*" if comp.wilcoxon_p < 0.05 else "ns"
                print(f"  Wilcoxon p:      {comp.wilcoxon_p:.4f} ({sig})")
            if comp.tost_p is not None:
                eq = "YES" if comp.equivalent else "NO"
                print(f"  TOST p:          {comp.tost_p:.4f} (equivalent={eq})")
            print()

    # Token savings
    if report.token_savings:
        print(f"--- Token Savings vs Markdown ---\n")
        for fmt, savings in sorted(report.token_savings.items()):
            print(f"  {fmt}: {savings:.1f}%")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python bench/v2/stats.py <results_path>", file=sys.stderr)
        sys.exit(1)

    results_path = Path(sys.argv[1])
    report = analyze(results_path)
    print_report(report)


if __name__ == "__main__":
    main()
