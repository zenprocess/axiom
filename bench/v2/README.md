# AxiomBench v2 -- Statistically Rigorous Compliance Benchmark

Benchmark suite for measuring compliance rate across rule encoding formats
(markdown, TOON, CACP) with proper experimental design and statistical analysis.

## Quick Start

```bash
# Quick validation (48 calls, ~35 min)
python bench/v2/runner.py --phase quick

# Sonnet baseline (96 calls, ~70 min)
python bench/v2/runner.py --phase baseline --model sonnet --runs 4

# Opus baseline (96 calls, ~70 min)
python bench/v2/runner.py --phase baseline --model opus --runs 4

# Full experiment (240 calls, ~3 hours)
python bench/v2/runner.py --phase final --runs 5

# 20 rounds per model
python bench/v2/runner.py --phase final --model sonnet --runs 20
python bench/v2/runner.py --phase final --model opus --runs 20

# Full overnight run (480 calls, ~6 hours)
python bench/v2/runner.py --phase overnight

# Analyze results
python bench/v2/stats.py bench/v2/results/

# Generate paper tables
python bench/v2/report.py bench/v2/results/
```

## Phases

| Phase | Models | Runs | Total Calls | Time |
|-------|--------|------|-------------|------|
| quick | sonnet | 2 | 48 | ~35 min |
| baseline | sonnet | 4 | 96 | ~70 min |
| final | sonnet+opus | 5 | 240 | ~3 hours |
| overnight | sonnet+opus | 10 | 480 | ~6 hours |

## Experimental Design

**Full factorial**: 8 tasks x 3 formats x N models x R runs

- **Tasks**: 8 coding tasks that probe specific compliance boundaries
- **Formats**: markdown (verbose baseline), TOON (Axiom tabular), CACP (structured sections)
- **Models**: claude-sonnet-4-6, claude-opus-4-6
- **Rules**: 10 compliance rules with automated regex checks

## Statistical Analysis

- Per-cell mean + std + 95% CI (bootstrap, 1000 resamples)
- Wilcoxon signed-rank test: TOON vs markdown, CACP vs markdown
- TOST equivalence test: is |diff| < 5%?
- Cohen's d effect size
- Per-rule violation frequency heatmap
- Format x model interaction analysis

## Resume Support

Results are saved incrementally to JSONL. If the process crashes, rerun with
the same --output-dir to resume from where it left off.

## Autoresearch

Autonomous format tuning loop:

```bash
python bench/v2/autoresearch.py --model sonnet --max-experiments 20
```

Iteratively mutates TOON format parameters and keeps improvements.

## Files

- `config.py` -- Experiment configuration (models, phases, paths)
- `rules.py` -- 10 compliance rules with automated checks
- `tasks.py` -- 8 coding tasks
- `formats.py` -- Rule format generators (markdown, TOON, CACP)
- `runner.py` -- Main experiment runner with resume support
- `stats.py` -- Statistical analysis (bootstrap CI, Wilcoxon, TOST, Cohen's d)
- `report.py` -- Paper-ready table generation
- `autoresearch.py` -- Autonomous format tuning
