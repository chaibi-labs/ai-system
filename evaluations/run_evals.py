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
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = REPO_ROOT / "evaluations" / "tasks"
EXPECTED_DIR = REPO_ROOT / "evaluations" / "expected"
REPORTS_DIR = REPO_ROOT / "evaluations" / "reports"
HALT_FILE = Path("~/.ai-system/HALT").expanduser()

DEFAULT_MODEL = "qwen2.5-coder:14b"
OLLAMA_API_URL = "http://localhost:11434/api/generate"
EXEC_TIMEOUT_SECONDS = 900       # 15 min per executor run
ACCEPT_TIMEOUT_SECONDS = 300     # 5 min for the acceptance_check command
RAW_OUTPUT_TRUNCATE = 4000       # cap raw output stored in the report

# The model sometimes wraps its entire output in markdown code fences. Strip
# outer ```...``` before parsing file blocks.
OUTER_FENCE_RE = re.compile(r"\A\s*```[a-zA-Z]*\s*\n(.*)\n```\s*\Z", re.DOTALL)

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
    """Build a slim eval-mode prompt.

    We deliberately do NOT include policies/universal.md or
    prompts/coder-executor.md verbatim. Those are written for the production
    tool-use loop where the model calls tools (write_file, run_tests) and
    emits a "What I did / Tests run / ..." universal output block at the end.
    For one-shot text-generation evals, that universal output format CONFLICTS
    with the file-block format the harness needs to parse. So we re-state the
    relevant discipline (stay-in-scope, no unlisted deps, BLOCKED-on-ambiguity)
    in eval-specific phrasing, and force the file-block + STATUS output format.
    """
    tree_lines = list_tree(fixture_dir)
    tree = "\n".join(tree_lines) if tree_lines else "(empty)"
    spec_str = json.dumps(task_spec, indent=2, default=str)

    return f"""You are evaluating the executor stage of a specifier-executor coding pipeline. \
You receive a structured task_spec and a fixture file tree. Your job: produce file content that implements the spec.

# task_spec

```json
{spec_str}
```

# Current fixture file tree (relative paths from repo root)

```
{tree}
```

# Implementation rules

- Use ONLY the files listed in `task_spec.files_to_create_or_edit`. Don't touch anything else.
- Match `task_spec.function_signatures` exactly. For a NEW file, create the file AND the function with that exact signature.
- Add the test files and cases listed in `task_spec.test_files_and_cases`.
- Stay within `task_spec.expected_diff_shape` per file (treat it as a per-file budget).
- Do not violate `task_spec.out_of_scope`.
- Do not add dependencies outside `task_spec.allowed_new_dependencies`. If a new dep would be needed but isn't listed, emit STATUS BLOCKED instead.

# Output format — STRICT, machine-parsed

For each file you create or modify, emit EXACTLY:

```
=== BEGIN FILE: <relative/path> ===
<full file content, no truncation, no placeholders>
=== END FILE: <relative/path> ===
```

After all file blocks, emit EXACTLY one of:

```
=== STATUS ===
DONE
```

or

```
=== STATUS ===
BLOCKED: <one specific question or contradiction>
```

# Output discipline (read carefully — overrides any other format you've been trained on)

- Emit ONLY file blocks and the STATUS marker. No prose, no preamble, no markdown headers, no commentary.
- Do NOT emit a "What I did / Tests run / Risk / Cost flags / Decisions needed / Heartbeat" block. That format applies in the production tool-use loop, NOT in this eval. Use ONLY the file-block + STATUS format above.
- Use the EXACT same path string in BEGIN and END markers for a given file.
- Do not wrap the blocks in extra code fences. The markers ARE the delimiters.
- Do not add any text after the STATUS marker.
- If something in the task_spec is genuinely ambiguous (not just "I'd choose differently"), emit STATUS BLOCKED with the specific question. Do not guess. But default to attempting the implementation — only BLOCKED for real contradictions.
"""


def strip_outer_fence(text: str) -> str:
    """If the entire output is wrapped in ```...```, strip the outer fence."""
    m = OUTER_FENCE_RE.match(text)
    return m.group(1) if m else text


def parse_and_apply_output(output: str, fixture_dir: Path) -> dict:
    """Parse model output, write the file blocks into fixture_dir, return status."""
    output = strip_outer_fence(output)
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
    if status_match:
        # The capture may pick up trailing backticks if the model fenced its output.
        status = status_match.group("status").strip().rstrip("`").strip()
    else:
        status = "MISSING_STATUS"

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


def call_ollama_api(model: str, prompt: str, timeout: int) -> tuple[str, str | None]:
    """Call Ollama HTTP API. Returns (response_text, error_or_None).

    Using the API gives us clean text output without the ANSI/cursor-control
    codes the `ollama run` CLI emits for its streaming UI even when stdin is
    piped.
    """
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        OLLAMA_API_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        return "", f"ollama API URLError: {exc}"
    except TimeoutError:
        return "", f"ollama API timeout after {timeout}s"
    except json.JSONDecodeError as exc:
        return "", f"ollama API returned non-JSON: {exc}"
    if "response" not in body:
        return "", f"ollama API response missing 'response' key: {body}"
    return body["response"], None


def execute_real(task_spec: dict, expected: dict, fixture_dir: Path, model: str) -> dict:
    prompt = build_executor_prompt(task_spec, fixture_dir)

    raw, err = call_ollama_api(model, prompt, EXEC_TIMEOUT_SECONDS)
    if err:
        return {
            "executed": True,
            "executor_status": "ollama_error",
            "verdict": "fail",
            "model": model,
            "error": err,
        }
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
