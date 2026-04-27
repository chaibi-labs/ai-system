#!/usr/bin/env python3
"""
repo_health.py — sanity check that the ai-system repo still has its expected
shape. Runs on demand and as a nightly precondition.

Stdlib only. Exits 0 on green, 1 on yellow (warnings), 2 on red (missing
load-bearing files).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


REQUIRED_FILES = [
    "README.md",
    "AGENTS.md",
    ".gitignore",
    "prompts/coder-planner.md",
    "prompts/coder-executor.md",
    "prompts/pm.md",
    "prompts/nightly.md",
    "policies/universal.md",
    "policies/cost-policy.md",
    "policies/cost-gates.yaml",
    "policies/github-policy.md",
    "policies/release-policy.md",
    "policies/security-policy.md",
    "policies/codex-usage.md",
    "policies/mobile-policy.md",
    "policies/nightly-policy.md",
    "policies/liveness-policy.md",
    "policies/liveness-budgets.yaml",
    "policies/session-bootstrap.md",
    "templates/task_spec_example.yaml",
    "templates/decision_record.md",
    "templates/pr_template.md",
    "templates/product_brief.md",
    "agents/pm.yaml",
    "agents/architect.yaml",
    "agents/coder.yaml",
    "agents/reviewer.yaml",
    "agents/qa.yaml",
    "agents/design.yaml",
    "agents/ops.yaml",
    "agents/research.yaml",
    "agents/nightly.yaml",
    "workflows/new-product.yaml",
    "workflows/feature-development.yaml",
    "workflows/figma-to-website.yaml",
    "workflows/mobile-app.yaml",
    "workflows/nightly-system-improvement.yaml",
    "scripts/codex_quota_probe.py",
    "scripts/repo_health.py",
    ".github/PULL_REQUEST_TEMPLATE.md",
]

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
    "skills",
    ".github",
]


def check() -> dict:
    missing_files: list[str] = []
    missing_dirs: list[str] = []
    empty_files: list[str] = []

    for d in REQUIRED_DIRS:
        if not (REPO_ROOT / d).is_dir():
            missing_dirs.append(d)

    for f in REQUIRED_FILES:
        p = REPO_ROOT / f
        if not p.is_file():
            missing_files.append(f)
        elif p.stat().st_size == 0:
            empty_files.append(f)

    if missing_files or missing_dirs:
        verdict = "red"
    elif empty_files:
        verdict = "yellow"
    else:
        verdict = "green"

    return {
        "verdict": verdict,
        "missing_dirs": missing_dirs,
        "missing_files": missing_files,
        "empty_files": empty_files,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
    }


def main() -> int:
    report = check()
    print(json.dumps(report, indent=2))
    return {"green": 0, "yellow": 1, "red": 2}[report["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
