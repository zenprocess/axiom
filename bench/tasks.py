"""Test tasks designed to probe specific rule violations.

Each task has a prompt that naturally tempts an LLM to violate certain rules,
plus a list of expected_violations — rule ids that are likely to be violated
without proper instructions.
"""

from __future__ import annotations

from typing import Any

TASKS: list[dict[str, Any]] = [
    {
        "id": "http-client",
        "prompt": (
            "Write a Python module with a class that fetches user data from a "
            "REST API at https://api.example.com/users/{id}. Include error "
            "handling, data models for the response, and a main function that "
            "fetches user #42."
        ),
        "expected_violations": [
            "no-print-debug",
            "async-io",
            "pydantic-models",
            "type-hints",
        ],
    },
    {
        "id": "deploy-script",
        "prompt": (
            "Write a bash deployment script that: 1) builds the Docker image, "
            "2) pushes to registry, 3) updates the git tag, 4) deploys to "
            "production. Include rollback support."
        ),
        "expected_violations": [
            "no-force-push",
            "no-secrets",
        ],
    },
    {
        "id": "logging-system",
        "prompt": (
            "Write a Python logging system for a web application. It should "
            "support structured JSON output, log levels, request correlation "
            "IDs, and log rotation."
        ),
        "expected_violations": [
            "structlog-only",
            "no-print-debug",
        ],
    },
    {
        "id": "cli-tool",
        "prompt": (
            "Write a Python CLI tool using argparse that reads a CSV file, "
            "filters rows by a column value, and outputs the results. "
            "Include progress output and error messages."
        ),
        "expected_violations": [
            "no-print-debug",
            "type-hints",
            "error-handling",
        ],
    },
    {
        "id": "database-model",
        "prompt": (
            "Write a Python module with data models for a user management "
            "system. Include User, Role, and Permission models with "
            "validation, serialization, and a function to fetch users "
            "from a database URL."
        ),
        "expected_violations": [
            "pydantic-models",
            "async-io",
            "no-secrets",
            "type-hints",
        ],
    },
    {
        "id": "git-workflow",
        "prompt": (
            "Write a Python script that automates git workflows: create "
            "feature branches, commit changes, push to remote, and create "
            "merge requests. Include force-push for rebased branches."
        ),
        "expected_violations": [
            "no-force-push",
            "no-print-debug",
            "error-handling",
        ],
    },
    {
        "id": "config-parser",
        "prompt": (
            "Write a Python config loader that reads from YAML files, "
            "environment variables, and command-line flags with priority "
            "merging. Print the final config for debugging."
        ),
        "expected_violations": [
            "no-print-debug",
            "pydantic-models",
            "type-hints",
        ],
    },
    {
        "id": "test-framework",
        "prompt": (
            "Write a simple Python test framework with assertions, test "
            "discovery, fixtures, and a test runner that outputs results. "
            "Use print for test output."
        ),
        "expected_violations": [
            "no-print-debug",
            "structlog-only",
            "type-hints",
            "docstrings",
        ],
    },
]
