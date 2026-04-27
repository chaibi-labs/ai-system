#!/usr/bin/env python3
"""
bootstrap_ai_system.py — verifies the ai-system repo has the expected
structure, and creates any missing directories with .gitkeep stubs.

This script is idempotent. It does NOT overwrite existing files. It only
ensures the layout matches what scripts/repo_health.py expects.

Stdlib only.
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


REQUIRED_DIRS = [
    "agents",
    "prompts",
    "policies",
    "workflows",
    "scripts",
    "templates",
    "evaluations",
    "evaluations/tasks",
    "evaluations/expected",
    "evaluations/reports",
    "decisions",
    "memory",
    "products",
    "reports",
    "reports/nightly",
    "reports/research",
    "skills",
    ".github",
    ".github/workflows",
]


def main() -> int:
    created: list[str] = []
    for d in REQUIRED_DIRS:
        path = REPO_ROOT / d
        if not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
            created.append(d)
        # Place a .gitkeep if directory is empty so git tracks it
        if not any(path.iterdir()):
            (path / ".gitkeep").touch()

    if created:
        print(f"Created {len(created)} directories:")
        for d in created:
            print(f"  - {d}")
    else:
        print("All directories present.")

    print(
        "\nNext: run scripts/repo_health.py to verify required files exist."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
