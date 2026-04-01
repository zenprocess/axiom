"""Experiment configuration for AxiomBench v2."""

from __future__ import annotations

FORMATS: list[str] = ["markdown", "toon", "cacp"]

MODELS: list[str] = ["sonnet", "opus"]

MODEL_IDS: dict[str, str] = {
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
}

RUNS_PER_CELL: int = 5

CLAUDE_BIN: str = "/home/vvladescu/.local/bin/claude"

CALL_TIMEOUT: int = 300  # seconds per Claude call

# Phase definitions: (models, runs_per_cell)
PHASES: dict[str, dict] = {
    "quick": {
        "description": "Fast validation",
        "models": ["sonnet"],
        "runs": 2,
    },
    "baseline": {
        "description": "Single-model baseline",
        "models": ["sonnet"],
        "runs": 4,
    },
    "final": {
        "description": "Full dual-model experiment",
        "models": ["sonnet", "opus"],
        "runs": 5,
    },
    "overnight": {
        "description": "High-power overnight run",
        "models": ["sonnet", "opus"],
        "runs": 10,
    },
}

# Clean PATH to avoid RTK hook rewriting claude calls
CLEAN_PATH: str = "/usr/local/bin:/usr/bin:/bin:/home/vvladescu/.local/bin"
