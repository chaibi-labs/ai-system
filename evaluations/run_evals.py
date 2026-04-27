#!/usr/bin/env python3
"""
run_evals.py — runner for the regression suite.

For each task in evaluations/tasks/, the harness:
  1. Materializes the fixture into a fresh temp dir.
  2. Runs the executor — either a real `ollama run <model>` call (if ollama is
     on PATH and `--stub` is not set), or the stub fallback.
  3. Parses the model's `=== BEGIN FILE: path === / === END FILE: path ===`
     blocks and writes them into the fixture.
  4. Runs `task_spec.acceptance_check`.
  5. Validates against expected/<NN>_expected.json: forbidden-modify check,
     expected-files-created check, BLOCKED-status handling.
  6. Writes evaluations/reports/<date>-<commit>.md.

CI auto-falls-back to stub mode (no ollama on GitHub-hosted runners), so the
gate stays passing until the host runs the harness against a real model.

Codex (planner) is intentionally NOT invoked here — task_specs are pre-authored
in tasks/<NN>_*.yaml and serve as the ground truth being tested. A separate
planner-eval mode is a future addition.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
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

DEFAULT_MODEL = "qwen2.5-coder:14b"
EXEC_TIMEOUT_SECONDS = 900       # 15 min per executor run
ACCEPT_TIMEOUT_SECONDS = 300     # 5 min for the acceptance_check command
RAW_OUTPUT_TRUNCATE = 4000       # cap raw output stored in the report

FILE_BLOCK_RE = re.compile(
    r"===\s*BEGIN FILE:\s*(?P<path>.+?)\s*===\s*\n(?P<body>.*?)===\s*END FILE:\s*(?P=path)\s*===",
    re.DOTALL,
)
STATUS_RE = re.compile(
    r"===\s*STATUS\s*===\s*(?P<status>.+?)(?:\Z|\n===)",
    re.DOTALL,
)


def halted() -> bool:
    return HALT_FILE.exists()


def parse_yaml(text: str) -> dict:
    try:
        out = subprocess.run(
            ["yq", "-o", "json"], input=text, check=True, capture_output=True, text=True
        ).stdout
        return json.loads(out)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            f"yq is required to parse eval task YAML ({exc}). Install mikefarah/yq."
        )


def materialize_fixture(task: dict, into: Path) -> None:
    starter = task.get("fixture", {}).get("starter", {})
    for rel_path, content in starter.items():
        target = into / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            target.write_text(content, encoding="utf-8")
        else:
            target.write_text(json.dumps(content), encoding="utf-8")


def list_tree(root: Path) -> list[str]:
    files = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            files.append(str(p.relative_to(root)))
    return files


def build_executor_prompt(task_spec: dict, fixture_dir: Path) -> str:
    universal_path = REPO_ROOT / "policies" / "universal.md"
    executor_path = REPO_ROOT / "prompts" / "coder-executor.md"

    universal = universal_path.read_text() if universal_path.exists() else ""
    executor = executor_path.read_text() if executor_path.exists() else ""

    tree_lines = list_tree(fixture_dir)
    tree = "\n".join(tree_lines) if tree_lines else "(empty)"

    spec_yaml_like = json.dumps(task_spec, indent=2, default=str)

    return f"""{universal}

---

{executor}

---

# task_spec

```json
{spec_yaml_like}
```

# Current fixture file tree (relative paths)

```
{tree}
```

# Output format — eval mode (REQUIRED, machine-parsed)

For each file you create or modify, emit a block in EXACTLY this format:

```
=== BEGIN FILE: <relative/path> ===
<full file content here, no truncation, no placeholders>
=== END FILE: <relative/path> ===
```

After all file blocks, emit one of:

```
=== STATUS ===
DONE
```

or

```
=== STATUS ===
BLOCKED: <one specific question or contradiction>
```

Strict rules for this output format:
- Emit ONLY file blocks and the STATUS marker. No prose, no markdown headers, no preamble.
- Use the EXACT same path string in BEGIN and END markers for a given file.
- Do not wrap the blocks in additional code fences. The block markers ARE the delimiters.
- Do not add any text after the STATUS marker.
- If anything in the task_spec is ambiguous, emit STATUS BLOCKED with the specific question. Do not guess.
"""


def parse_and_apply_output(output: str, fixture_dir: Path) -> dict:
    """Parse model output, write the file blocks into fixture_dir, return status."""
    files_written: list[str] = []
    seen: set[str] = set()
    for m in FILE_BLOCK_RE.finditer(output):
        rel = m.group("path").strip()
        if rel in seen:
            continue
        seen.add(rel)
        body = m.group("body")
        if body.startswith("\n"):
            body = body[1:]
        target = fixture_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        files_written.append(rel)

    status_match = STATUS_RE.search(output)
    status = status_match.group("status").strip() if status_match else "MISSING_STATUS"

    return {"files_written": files_written, "status": status}


def run_acceptance(task_spec: dict, fixture_dir: Path) -> dict:
    cmd = task_spec.get("acceptance_check", {}).get("command", "")
    if not cmd:
        return {"returncode": -1, "stdout": "", "stderr": "no acceptance_check command"}
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=fixture_dir,
            capture_output=True,
            text=True,
            timeout=ACCEPT_TIMEOUT_SECONDS,
        )
        return {
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-1500:],
            "stderr_tail": result.stderr[-500:],
        }
    except subprocess.TimeoutExpired:
        return {
            "returncode": -1,
            "stdout_tail": "",
            "stderr_tail": f"timeout after {ACCEPT_TIMEOUT_SECONDS}s",
        }


def validate(expected: dict, applied: dict, accept: dict) -> dict:
    """Compare applied changes + acceptance result to expected JSON."""
    issues: list[str] = []

    if expected.get("acceptance") == "pass" and accept["returncode"] != 0:
        issues.append(f"acceptance failed (rc={accept['returncode']})")

    forbidden = set(expected.get("must_not_modify", []))
    touched = set(applied["files_written"])
    overlap = forbidden & touched
    if overlap:
        issues.append(f"forbidden files modified: {sorted(overlap)}")

    expected_created = set(expected.get("files_created", []))
    if expected_created and not expected_created.issubset(touched):
        missing = sorted(expected_created - touched)
        issues.append(f"expected files not created: {missing}")

    if applied["status"].startswith("BLOCKED"):
        issues.append(f"executor returned BLOCKED: {applied['status']}")
    elif applied["status"] == "MISSING_STATUS":
        issues.append("executor did not emit a STATUS marker")

    return {"all_constraints_met": not issues, "issues": issues}


def execute_stub(task_spec: dict, fixture_dir: Path) -> dict:
    cmd = task_spec.get("acceptance_check", {}).get("command", "")
    result = subprocess.run(cmd, shell=True, cwd=fixture_dir, capture_output=True, text=True)
    return {
        "executed": False,
        "executor_status": "stubbed",
        "verdict": "skipped",
        "acceptance_returncode": result.returncode,
        "note": "ollama not available — stub returned without modifying the fixture",
    }


def execute_real(task_spec: dict, expected: dict, fixture_dir: Path, model: str) -> dict:
    prompt = build_executor_prompt(task_spec, fixture_dir)

    try:
        proc = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=EXEC_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {
            "executed": True,
            "executor_status": "timeout",
            "verdict": "fail",
            "model": model,
            "note": f"ollama run timed out after {EXEC_TIMEOUT_SECONDS}s",
        }

    if proc.returncode != 0:
        return {
            "executed": True,
            "executor_status": "ollama_error",
            "verdict": "fail",
            "model": model,
            "stderr_tail": proc.stderr[-500:],
        }

    raw = proc.stdout
    applied = parse_and_apply_output(raw, fixture_dir)
    accept = run_acceptance(task_spec, fixture_dir)
    val = validate(expected, applied, accept)

    return {
        "executed": True,
        "executor_status": "completed",
        "verdict": "pass" if val["all_constraints_met"] else "fail",
        "model": model,
        "files_written": applied["files_written"],
        "executor_status_marker": applied["status"],
        "acceptance_returncode": accept["returncode"],
        "acceptance_stdout_tail": accept["stdout_tail"],
        "acceptance_stderr_tail": accept["stderr_tail"],
        "validation": val,
        "raw_output_len": len(raw),
        "raw_output_head": raw[:RAW_OUTPUT_TRUNCATE],
    }


def execute(task_spec: dict, expected: dict, fixture_dir: Path, model: str, force_stub: bool) -> dict:
    if force_stub or shutil.which("ollama") is None:
        return execute_stub(task_spec, fixture_dir)
    return execute_real(task_spec, expected, fixture_dir, model)


def run_one(task_path: Path, model: str, force_stub: bool) -> dict:
    task_name = task_path.stem
    task = parse_yaml(task_path.read_text())

    expected_path = EXPECTED_DIR / f"{task_name.split('_')[0]}_expected.json"
    expected = json.loads(expected_path.read_text()) if expected_path.exists() else {}

    with tempfile.TemporaryDirectory(prefix=f"eval-{task_name}-") as tmp:
        fixture_dir = Path(tmp)
        materialize_fixture(task, fixture_dir)
        result = execute(task["task_spec"], expected, fixture_dir, model, force_stub)

    return {
        "task": task_name,
        "expected_summary": {
            "files_created": expected.get("files_created", []),
            "must_not_modify": expected.get("must_not_modify", []),
            "test_pass_count": expected.get("test_pass_count"),
        },
        "result": result,
        "verdict": result.get("verdict", "tbd"),
    }


def write_report(runs: list[dict], model: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()
    commit = "uncommitted"
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
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
        f"- model:   {model}",
        f"- total:   {summary['total']}",
        f"- passed:  {summary['passed']}",
        f"- failed:  {summary['failed']}",
        f"- skipped: {summary['skipped']}",
        "",
        "## Per-task",
        "",
    ]
    for r in runs:
        body.append(f"### {r['task']} — {r['verdict']}")
        body.append("```json")
        body.append(json.dumps(r["result"], indent=2)[:RAW_OUTPUT_TRUNCATE * 2])
        body.append("```")
        body.append("")
    out_path.write_text("\n".join(body), encoding="utf-8")
    return out_path


def main() -> int:
    if halted():
        print("HALT file present; eval run aborted.", file=sys.stderr)
        return 0

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task", help="run a single task by NN prefix, e.g. 01")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--stub", action="store_true",
                    help="force stub mode even if ollama is available")
    args = ap.parse_args()

    tasks = sorted(TASKS_DIR.glob("*.yaml"))
    if args.task:
        tasks = [t for t in tasks if t.name.startswith(args.task)]
    if not tasks:
        print("No matching tasks found.", file=sys.stderr)
        return 2

    have_ollama = shutil.which("ollama") is not None
    if args.stub or not have_ollama:
        print(f"Mode: stub  (ollama_present={have_ollama}, --stub={args.stub})", flush=True)
    else:
        print(f"Mode: real   model={args.model}", flush=True)

    runs: list[dict] = []
    for t in tasks:
        print(f"== {t.name} ==", flush=True)
        runs.append(run_one(t, args.model, args.stub))

    report_path = write_report(runs, args.model)
    print(f"Report: {report_path.relative_to(REPO_ROOT)}")

    failed = sum(1 for r in runs if r["verdict"] == "fail")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
