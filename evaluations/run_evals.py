#!/usr/bin/env python3
"""
run_evals.py — runner skeleton for the regression suite.

This script:
  1. For each task in evaluations/tasks/, materializes the fixture into a
     fresh temp dir.
  2. Hands the task_spec to the configured executor (currently a stub —
     populated when nightly v3+ wires real local-model execution).
  3. Runs the task_spec.acceptance_check command.
  4. Compares observed file changes / test counts to the expected JSON.
  5. Writes evaluations/reports/<date>-<commit>.md.

The executor stub returns "not_implemented" for now — the harness still
verifies the suite is *runnable* (fixtures materialize, expected files load,
diffs are computable). Once the autonomous studio is operational, the
executor stub will be replaced by the real `coder.execute` call.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = REPO_ROOT / "evaluations" / "tasks"
EXPECTED_DIR = REPO_ROOT / "evaluations" / "expected"
REPORTS_DIR = REPO_ROOT / "evaluations" / "reports"
HALT_FILE = Path("~/.ai-system/HALT").expanduser()


def halted() -> bool:
    return HALT_FILE.exists()


def parse_yaml_minimal(text: str) -> dict:
    """Tiny YAML parser tuned for our eval task files. Falls back to yq if available.

    Our YAML uses only:
      - scalars
      - lists (- item)
      - nested maps (two-space indent)
      - block scalars (| ... )
    For robustness, prefer `yq` when present.
    """
    try:
        out = subprocess.run(
            ["yq", "-o", "json"], input=text, check=True, capture_output=True, text=True
        ).stdout
        return json.loads(out)
    except (FileNotFoundError, subprocess.CalledProcessError):
        # Defer to a runtime error the caller can surface
        raise RuntimeError(
            "yq is required to parse eval task YAML. Install yq (apt or brew) "
            "or convert task files to JSON."
        )


def materialize_fixture(task: dict, into: Path) -> None:
    fixture = task.get("fixture", {})
    starter = fixture.get("starter", {})
    for rel_path, content in starter.items():
        target = into / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")


def execute_stub(task_spec: dict, fixture_dir: Path) -> dict:
    """Placeholder executor.

    Returns a result that records "not_implemented" — runs the acceptance_check
    against the unmodified fixture (which will typically fail, since the spec
    expects new files). When the real executor is wired up, replace this with
    a call into `coder.execute`.
    """
    cmd = task_spec.get("acceptance_check", {}).get("command", "")
    # Run from fixture_dir using a shell, but capture not raise
    result = subprocess.run(
        cmd, shell=True, cwd=fixture_dir, capture_output=True, text=True
    )
    return {
        "executed": False,
        "executor_status": "not_implemented",
        "acceptance_command": cmd,
        "acceptance_returncode": result.returncode,
        "acceptance_stdout_tail": result.stdout[-500:],
        "acceptance_stderr_tail": result.stderr[-500:],
    }


def run_one(task_path: Path) -> dict:
    task_name = task_path.stem
    task = parse_yaml_minimal(task_path.read_text())

    expected_path = EXPECTED_DIR / f"{task_name.split('_')[0]}_expected.json"
    expected = json.loads(expected_path.read_text()) if expected_path.exists() else {}

    with tempfile.TemporaryDirectory(prefix=f"eval-{task_name}-") as tmp:
        fixture_dir = Path(tmp)
        materialize_fixture(task, fixture_dir)
        result = execute_stub(task["task_spec"], fixture_dir)

    return {
        "task": task_name,
        "expected": expected,
        "result": result,
        # Verdict will be "skipped" until executor is wired
        "verdict": "skipped" if not result.get("executed") else "tbd",
    }


def write_report(runs: list[dict]) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()
    commit = "uncommitted"
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        pass

    out_path = REPORTS_DIR / f"{today}-{commit}.md"
    summary = {
        "total": len(runs),
        "skipped": sum(1 for r in runs if r["verdict"] == "skipped"),
        "passed": sum(1 for r in runs if r["verdict"] == "pass"),
        "failed": sum(1 for r in runs if r["verdict"] == "fail"),
    }
    body = [
        f"# Eval Run — {today} ({commit})",
        "",
        f"- total: {summary['total']}",
        f"- skipped: {summary['skipped']}",
        f"- passed: {summary['passed']}",
        f"- failed: {summary['failed']}",
        "",
        "## Per-task",
        "",
    ]
    for r in runs:
        body.append(f"### {r['task']} — {r['verdict']}")
        body.append("```json")
        body.append(json.dumps(r["result"], indent=2))
        body.append("```")
        body.append("")
    out_path.write_text("\n".join(body), encoding="utf-8")
    return out_path


def main() -> int:
    if halted():
        print("HALT file present; eval run aborted.", file=sys.stderr)
        return 0

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task", help="run a single task by NN prefix, e.g., 01")
    ap.add_argument("--model", default="qwen2.5-coder:14b")
    args = ap.parse_args()

    tasks = sorted(TASKS_DIR.glob("*.yaml"))
    if args.task:
        tasks = [t for t in tasks if t.name.startswith(args.task)]
    if not tasks:
        print("No matching tasks found.", file=sys.stderr)
        return 2

    runs: list[dict] = []
    for t in tasks:
        print(f"== {t.name} ==")
        runs.append(run_one(t))

    report_path = write_report(runs)
    print(f"Report: {report_path.relative_to(REPO_ROOT)}")
    return 0 if all(r["verdict"] in ("pass", "skipped") for r in runs) else 1


if __name__ == "__main__":
    sys.exit(main())
