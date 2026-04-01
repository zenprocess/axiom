# Axiom Compliance Benchmark

A/B compliance benchmark comparing Axiom compiled rules against conventional markdown rules.

## Overview

- **10 rules** with automated regex-based compliance checks (`rules.py`)
- **8 coding tasks** designed to tempt specific rule violations (`tasks.py`)
- **A/B runner** that invokes Claude with both formats and compares compliance (`runner.py`)
- **Format parameters** controlling Axiom compilation (`format.py`)
- **Raw results** from 20 runs with Claude Sonnet 4.6 (`results/`)

## Requirements

```bash
pip install tiktoken
```

Claude CLI must be installed and authenticated (`claude -p` must work).

## Running

### Dry run (no Claude invocation, validates check functions + format generation)

```bash
python bench/runner.py --mode dry
```

### A/B comparison (invokes Claude, costs money)

```bash
# All 8 tasks
python bench/runner.py --mode ab

# Single task
python bench/runner.py --mode ab --task http-client
```

### Aggregate results

```bash
python bench/aggregate.py
```

## Results (20 runs, Claude Sonnet 4.6)

| Metric | Markdown (1195 tok) | Axiom S/D (159 tok) |
|--------|---------------------|---------------------|
| Mean compliance | 91.0% | 90.5% |
| Token savings | -- | 86.7% |
| Wins / Losses / Ties | 5 / 5 / 10 | 5 / 5 / 10 |

See `results/` for raw JSON from all runs, and `results/results.tsv` for the 26-experiment autoresearch log.

## Autoresearch

The benchmark includes an autoresearch loop (inspired by Karpathy's autoresearch pattern) for autonomous format tuning. The loop modifies `format.py` parameters, runs A/B comparisons, and keeps changes that improve compliance or reduce tokens. See `results/results.tsv` for the full experiment log (26 experiments, from 495 tokens down to 159).

## File Structure

```
bench/
  rules.py          # 10 compliance rules with check functions
  tasks.py          # 8 coding tasks with expected violations
  runner.py         # A/B comparison runner (invokes Claude)
  format.py         # Tunable Axiom format parameters
  aggregate.py      # Compute aggregates from raw results
  results/
    full_run.json   # 8-task full run
    ab_*.json       # Individual A/B run results
    results.tsv     # 26-experiment autoresearch log
```
