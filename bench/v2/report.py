#!/usr/bin/env python3
"""Generate paper-ready tables and exports from AxiomBench v2 results.

Usage:
    python bench/v2/report.py bench/v2/results/
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

# Ensure script directory is importable
_script_dir = Path(__file__).resolve().parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

from stats import AnalysisReport, analyze, load_results


def generate_report(analysis: AnalysisReport, output_dir: Path) -> None:
    """Generate paper-ready outputs.

    Creates:
    - tables.md: Markdown tables for the paper
    - raw_data.csv: All results as CSV
    - summary.json: Key statistics as JSON
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_markdown_tables(analysis, output_dir / "tables.md")
    _write_summary_json(analysis, output_dir / "summary.json")
    print(f"Report generated in {output_dir}", file=sys.stderr)


def _write_markdown_tables(report: AnalysisReport, path: Path) -> None:
    """Write paper-ready markdown tables."""
    lines: list[str] = []

    # Table 1: Format x Model compliance
    lines.append("## Table 1: Compliance Rate by Format and Model")
    lines.append("")
    lines.append("| Format | Model | Mean | Std | 95% CI | N |")
    lines.append("|--------|-------|------|-----|--------|---|")
    for fmt, model_data in sorted(report.format_model_stats.items()):
        for model, cell in sorted(model_data.items()):
            lines.append(
                f"| {fmt} | {model} | {cell.mean:.3f} | {cell.std:.3f} | "
                f"[{cell.ci_low:.3f}, {cell.ci_high:.3f}] | {cell.n} |"
            )
    lines.append("")

    # Table 2: Per-task
    lines.append("## Table 2: Per-Task Compliance Breakdown")
    lines.append("")
    all_keys = sorted(set(
        k for tdata in report.task_stats.values() for k in tdata
    ))
    header = "| Task |" + " | ".join(all_keys) + " |"
    sep = "|------|" + " | ".join(["------" for _ in all_keys]) + " |"
    lines.append(header)
    lines.append(sep)
    for task, tdata in sorted(report.task_stats.items()):
        cols = []
        for k in all_keys:
            if k in tdata:
                cols.append(f"{tdata[k].mean:.3f}")
            else:
                cols.append("--")
        lines.append(f"| {task} | " + " | ".join(cols) + " |")
    lines.append("")

    # Table 3: Per-rule violation heatmap
    lines.append("## Table 3: Per-Rule Violation Rate by Format")
    lines.append("")
    all_fmts = sorted(set(
        f for rdata in report.rule_violations.values() for f in rdata
    ))
    header = "| Rule |" + " | ".join(all_fmts) + " |"
    sep = "|------|" + " | ".join(["------" for _ in all_fmts]) + " |"
    lines.append(header)
    lines.append(sep)
    for rule_id, rdata in sorted(report.rule_violations.items()):
        cols = []
        for f in all_fmts:
            rate = rdata.get(f, 0.0)
            cols.append(f"{rate:.1%}")
        lines.append(f"| {rule_id} | " + " | ".join(cols) + " |")
    lines.append("")

    # Statistical comparisons
    if report.comparisons:
        lines.append("## Statistical Comparisons (vs Markdown Baseline)")
        lines.append("")
        lines.append("| Comparison | Mean Diff | Cohen's d | Wilcoxon p | TOST p | Equivalent? |")
        lines.append("|------------|-----------|-----------|------------|--------|-------------|")
        for comp in report.comparisons:
            wilcoxon = f"{comp.wilcoxon_p:.4f}" if comp.wilcoxon_p is not None else "--"
            tost = f"{comp.tost_p:.4f}" if comp.tost_p is not None else "--"
            equiv = "Yes" if comp.equivalent else "No" if comp.equivalent is not None else "--"
            lines.append(
                f"| {comp.format_a} vs {comp.format_b} | "
                f"{comp.mean_diff:+.4f} | {comp.cohens_d:+.4f} | "
                f"{wilcoxon} | {tost} | {equiv} |"
            )
        lines.append("")

    # Token savings
    if report.token_savings:
        lines.append("## Token Savings vs Markdown")
        lines.append("")
        lines.append("| Format | Savings |")
        lines.append("|--------|---------|")
        for fmt, savings in sorted(report.token_savings.items()):
            lines.append(f"| {fmt} | {savings:.1f}% |")
        lines.append("")

    path.write_text("\n".join(lines))
    print(f"  Written: {path}", file=sys.stderr)


def _write_raw_csv(records: list[dict], path: Path) -> None:
    """Write raw results as CSV."""
    if not records:
        return

    fieldnames = [
        "task", "format", "model", "run", "status",
        "compliance_rate", "rules_tokens_approx", "elapsed_seconds",
        "timestamp", "error",
    ]
    # Add individual rule columns
    sample_scores = records[0].get("scores", {})
    rule_cols = sorted(sample_scores.keys())
    fieldnames.extend(rule_cols)

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            row = {k: rec.get(k, "") for k in fieldnames if k not in rule_cols}
            scores = rec.get("scores", {})
            for rule_id in rule_cols:
                row[rule_id] = scores.get(rule_id, "")
            writer.writerow(row)

    print(f"  Written: {path}", file=sys.stderr)


def _write_summary_json(report: AnalysisReport, path: Path) -> None:
    """Write summary statistics as JSON."""
    summary: dict = {
        "n_records": report.n_records,
        "format_model": {},
        "comparisons": [],
        "token_savings": report.token_savings,
    }

    for fmt, model_data in report.format_model_stats.items():
        summary["format_model"][fmt] = {}
        for model, cell in model_data.items():
            summary["format_model"][fmt][model] = {
                "mean": round(cell.mean, 4),
                "std": round(cell.std, 4),
                "ci_95": [round(cell.ci_low, 4), round(cell.ci_high, 4)],
                "n": cell.n,
            }

    for comp in report.comparisons:
        summary["comparisons"].append({
            "comparison": f"{comp.format_a} vs {comp.format_b}",
            "mean_diff": round(comp.mean_diff, 4),
            "cohens_d": round(comp.cohens_d, 4) if comp.cohens_d else None,
            "wilcoxon_p": round(comp.wilcoxon_p, 4) if comp.wilcoxon_p is not None else None,
            "tost_p": round(comp.tost_p, 4) if comp.tost_p is not None else None,
            "equivalent": comp.equivalent,
        })

    path.write_text(json.dumps(summary, indent=2))
    print(f"  Written: {path}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python bench/v2/report.py <results_path> [output_dir]", file=sys.stderr)
        sys.exit(1)

    results_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else results_path / "report"

    report = analyze(results_path)

    # Also write raw CSV
    records = load_results(results_path)
    generate_report(report, output_dir)
    _write_raw_csv(records, output_dir / "raw_data.csv")


if __name__ == "__main__":
    main()
