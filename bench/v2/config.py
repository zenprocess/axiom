"""Experiment configuration for AxiomBench v2."""

from __future__ import annotations

import os
import shutil

FORMATS: list[str] = ["markdown", "toon", "cacp"]

MODELS: list[str] = ["sonnet", "opus", "hermes"]

MODEL_IDS: dict[str, str] = {
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
    "hermes": "qwen3-coder",
}

VLLM_ENDPOINT: str = os.environ.get("VLLM_ENDPOINT", "http://localhost:8000")
HERMES_ENGINE: str = os.environ.get("HERMES_ENGINE", "hermes-engine.py")

RUNS_PER_CELL: int = 5

CLAUDE_BIN: str = os.environ.get("CLAUDE_BIN", shutil.which("claude") or "claude")

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
        "description": "Full multi-model experiment",
        "models": ["sonnet", "opus", "hermes"],
        "runs": 5,
    },
    "overnight": {
        "description": "High-power overnight run",
        "models": ["sonnet", "opus", "hermes"],
        "runs": 10,
    },
}

# Clean PATH to avoid RTK hook rewriting claude calls
CLEAN_PATH: str = os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")
