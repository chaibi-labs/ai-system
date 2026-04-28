#!/usr/bin/env python3
"""
coder_execute.py — runs the Coder *executor* stage on a real GitHub issue.

Reads the task_spec from the issue (body first, then comments — latest wins),
clones the target repo to a temp dir, creates the target branch, runs the
local-model executor, applies the file blocks, runs the acceptance_check,
commits, pushes, and opens a PR.

Usage:
    python3 scripts/coder_execute.py <owner/repo> <issue-number> [--model M] [--dry-run]

If the executor returns BLOCKED, no PR is opened — instead a comment is
posted on the issue and the script exits non-zero. Per
`policies/liveness-policy.md` §22.5.2, more than 2 plan↔execute cycles
for one task should escalate to STUCK (enforced by the planner skill,
not here).

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HALT_FILE = Path("~/.ai-system/HALT").expanduser()
SECRETS_ENV = Path("~/.ai-system/secrets/.env").expanduser()

DEFAULT_MODEL = "qwen2.5-coder:14b"
OLLAMA_API_URL = "http://localhost:11434/api/generate"
EXEC_TIMEOUT_SECONDS = 900
ACCEPT_TIMEOUT_SECONDS = 600

GIT_AUTHOR_NAME = "DasGewuerz"
GIT_AUTHOR_EMAIL = "26594884+DasGewuerz@users.noreply.github.com"

FILE_BLOCK_RE = re.compile(
    r"===\s*BEGIN FILE:\s*(?P<path>.+?)\s*===\s*\n(?P<body>.*?)===\s*END FILE:\s*(?P=path)\s*===",
    re.DOTALL,
)
STATUS_RE = re.compile(
    r"===\s*STATUS\s*===\s*(?P<status>.+?)(?:\Z|\n===)",
    re.DOTALL,
)
OUTER_FENCE_RE = re.compile(r"\A\s*```[a-zA-Z]*\s*\n(.*)\n```\s*\Z", re.DOTALL)
TASK_SPEC_RE = re.compile(
    r"```ya?ml\s*\n(?P<yaml>.*?task_spec:.*?)\n```",
    re.DOTALL,
)


# ---------- pre-flight ----------------------------------------------------


def halted() -> bool:
    return HALT_FILE.exists()


def source_secrets() -> None:
    """Source GITHUB_TOKEN/GH_TOKEN from ~/.ai-system/secrets/.env into env."""
    if not SECRETS_ENV.exists():
        return
    for line in SECRETS_ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
    if "GH_TOKEN" not in os.environ and "GITHUB_TOKEN" in os.environ:
        os.environ["GH_TOKEN"] = os.environ["GITHUB_TOKEN"]


# ---------- gh helpers ----------------------------------------------------


def gh_json(args: list[str]):
    out = subprocess.run(
        ["gh"] + args, check=True, capture_output=True, text=True
    ).stdout
    return json.loads(out)


def fetch_issue(repo: str, number: int) -> dict:
    result = gh_json([
        "issue", "view", str(number),
        "--repo", repo,
        "--json", "body,title,number,comments,labels",
    ])
    if not isinstance(result, dict):
        raise RuntimeError(f"gh issue view returned non-dict: {type(result).__name__}")
    return result


# ---------- task_spec extraction ------------------------------------------


def extract_task_spec(text: str | None) -> dict | None:
    if not text:
        return None
    m = TASK_SPEC_RE.search(text)
    if not m:
        return None
    yaml_text = m.group("yaml")
    try:
        out = subprocess.run(
            ["yq", "-o", "json"],
            input=yaml_text, check=True, capture_output=True, text=True,
        ).stdout
        d = json.loads(out)
        return d.get("task_spec", d)
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return None


def find_task_spec(issue: dict) -> tuple[dict | None, str]:
    spec = extract_task_spec(issue.get("body"))
    if spec:
        return spec, "issue body"
    comments = issue.get("comments") or []
    for c in reversed(comments):
        spec = extract_task_spec(c.get("body"))
        if spec:
            return spec, f"comment {c.get('id', '?')}"
    return None, ""


# ---------- ollama -------------------------------------------------------


def call_ollama(model: str, prompt: str, timeout: int) -> tuple[str, str | None]:
    payload = json.dumps(
        {"model": model, "prompt": prompt, "stream": False}
    ).encode()
    req = urllib.request.Request(
        OLLAMA_API_URL, data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode())
        return body.get("response", ""), None
    except urllib.error.URLError as exc:
        return "", f"ollama URLError: {exc}"
    except TimeoutError:
        return "", f"ollama timeout after {timeout}s"
    except json.JSONDecodeError as exc:
        return "", f"ollama returned non-JSON: {exc}"


# ---------- prompt + parse ------------------------------------------------


def list_tree(root: Path, max_files: int = 600) -> list[str]:
    files: list[str] = []
    for p in sorted(root.rglob("*")):
        if any(part == ".git" or part.startswith(".git/") for part in p.parts):
            continue
        if p.is_file():
            files.append(str(p.relative_to(root)))
        if len(files) >= max_files:
            break
    return files


def build_executor_prompt(task_spec: dict, repo_root: Path) -> str:
    spec_str = json.dumps(task_spec, indent=2, default=str)
    tree = "\n".join(list_tree(repo_root))
    return f"""You are running the Coder executor stage. Implement the task_spec below against the current repo state.

# task_spec

```json
{spec_str}
```

# Current repo file tree (relative paths from repo root)

```
{tree}
```

# Implementation rules

- Use ONLY the files listed in `task_spec.files_to_create_or_edit`. Don't touch anything else.
- Match `task_spec.function_signatures` exactly. For NEW files, create the file AND the function with that exact signature.
- Add the test files and cases listed in `task_spec.test_files_and_cases`.
- Stay within `task_spec.expected_diff_shape` per file (treat it as a per-file budget).
- Do not violate `task_spec.out_of_scope`.
- Do not add dependencies outside `task_spec.allowed_new_dependencies`. If a new dep is needed but not listed, emit STATUS BLOCKED.
- IMPORTANT: emit COMPLETE file content for every file you touch. No diffs, no `...` placeholders, no truncation.

# Output format — STRICT, machine-parsed

For each file you create or modify, emit EXACTLY:

```
=== BEGIN FILE: <relative/path> ===
<full file content here>
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

# Output discipline (overrides any other format you've been trained on)

- Emit ONLY file blocks and the STATUS marker. No prose, no preamble, no commentary.
- Do NOT emit a "What I did / Tests run / Risk / Cost flags / Decisions needed / Heartbeat" block. That format is for the production tool-use loop, not this single-shot executor invocation.
- Same path string in BEGIN and END markers for a given file.
- Do not wrap blocks in extra code fences.
- Default to attempting the implementation — only BLOCKED for genuine contradictions.
"""


def strip_outer_fence(text: str) -> str:
    m = OUTER_FENCE_RE.match(text)
    return m.group(1) if m else text


def parse_output(output: str) -> dict:
    output = strip_outer_fence(output)
    blocks: list[tuple[str, str]] = []
    seen: set[str] = set()
    for m in FILE_BLOCK_RE.finditer(output):
        rel = m.group("path").strip()
        if rel in seen:
            continue
        seen.add(rel)
        body = m.group("body")
        if body.startswith("\n"):
            body = body[1:]
        blocks.append((rel, body))
    sm = STATUS_RE.search(output)
    if sm:
        status = sm.group("status").strip().rstrip("`").strip()
    else:
        status = "MISSING_STATUS"
    return {"blocks": blocks, "status": status}


def write_blocks(blocks: list[tuple[str, str]], repo_root: Path) -> list[str]:
    written: list[str] = []
    for rel, content in blocks:
        target = repo_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(rel)
    return written


# ---------- git/gh actions ------------------------------------------------


def run(cmd: list[str], cwd: Path | None = None, check: bool = True, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=cwd, check=check, capture_output=True, text=True, timeout=timeout
    )


def clone_repo(repo: str, into: Path) -> Path:
    target = into / repo.split("/")[-1]
    run(["gh", "repo", "clone", repo, str(target)], timeout=120)
    return target


def has_staged_changes(repo_dir: Path) -> bool:
    res = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo_dir, capture_output=True, text=True,
    )
    return res.returncode != 0


def parse_expected_diff_budget(entry: object) -> dict[str, object]:
    """Parse a per-file expected_diff_shape entry into numeric guard limits."""
    if isinstance(entry, dict):
        return {
            "max_added_lines": int(entry.get("max_added_lines", 0)),
            "max_deleted_lines": int(entry.get("max_deleted_lines", 0)),
            "forbid_rewrite": bool(entry.get("forbid_rewrite", False)),
        }

    text = str(entry).lower()
    added_match = re.search(r"~?\s*(\d+)\s+(?:added|inserted)", text)
    deleted_match = re.search(r"~?\s*(\d+)\s+deleted", text)
    max_added = int(added_match.group(1)) if added_match else 0
    max_deleted = int(deleted_match.group(1)) if deleted_match else 0
    if "inserted lines only" in text or "no-other-edits" in text:
        max_deleted = 0
    forbid_rewrite = any(
        phrase in text
        for phrase in (
            "do not rewrite",
            "must be modified, not created",
            "inserted lines only",
            "preserve/no-other-edits",
        )
    )
    return {
        "max_added_lines": max_added,
        "max_deleted_lines": max_deleted,
        "forbid_rewrite": forbid_rewrite,
    }


def collect_staged_diff_stats(repo_dir: Path) -> dict[str, dict[str, int]]:
    """Return staged add/delete counts keyed by relative file path."""
    res = run(["git", "diff", "--cached", "--numstat"], cwd=repo_dir, check=False)
    stats: dict[str, dict[str, int]] = {}
    for line in res.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added_s, deleted_s, path = parts
        added = 0 if added_s == "-" else int(added_s)
        deleted = 0 if deleted_s == "-" else int(deleted_s)
        stats[path] = {"added": added, "deleted": deleted}
    return stats


def scope_guard_violations(task_spec: dict, repo_dir: Path) -> list[str]:
    """Validate staged changes against task_spec file scope and diff budgets."""
    allowed_files = set(task_spec.get("files_to_create_or_edit") or [])
    diff_stats = collect_staged_diff_stats(repo_dir)
    violations: list[str] = []

    for path in sorted(diff_stats):
        if allowed_files and path not in allowed_files:
            violations.append(f"{path}: staged edit outside task_spec.files_to_create_or_edit")

    budgets: dict[str, dict[str, object]] = {}
    for entry in task_spec.get("expected_diff_shape") or []:
        if isinstance(entry, dict):
            for path, budget_entry in entry.items():
                budgets[path] = parse_expected_diff_budget(budget_entry)

    for path, budget in budgets.items():
        if path not in diff_stats:
            continue
        stats = diff_stats[path]
        max_added = int(budget.get("max_added_lines", 0))
        max_deleted = int(budget.get("max_deleted_lines", 0))
        forbid_rewrite = bool(budget.get("forbid_rewrite", False))
        if max_added and stats["added"] > max_added:
            violations.append(f"{path}: added lines {stats['added']} exceed budget {max_added}")
        if stats["deleted"] > max_deleted:
            violations.append(f"{path}: deleted lines {stats['deleted']} exceed budget {max_deleted}")
        if forbid_rewrite and stats["deleted"] > 0:
            violations.append(f"{path}: rewrite/delete blocked by expected_diff_shape")

    return violations


# ---------- main ----------------------------------------------------------


def main() -> int:
    if halted():
        print("HALT file present; coder_execute aborted.", file=sys.stderr)
        return 0

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repo", help="owner/repo, e.g. chaibi-labs/ai-system")
    ap.add_argument("issue", type=int, help="issue number")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--dry-run", action="store_true",
                    help="run executor and print diff but don't push or open PR")
    args = ap.parse_args()

    source_secrets()

    print(f"== fetching {args.repo}#{args.issue} ==", flush=True)
    issue = fetch_issue(args.repo, args.issue)
    spec, where = find_task_spec(issue)
    if not spec:
        print(
            f"No task_spec found in {args.repo}#{args.issue} (body or comments).",
            file=sys.stderr,
        )
        print("Run /plan first to emit a task_spec on the issue.", file=sys.stderr)
        return 2
    print(f"task_spec found in: {where}", flush=True)

    branch = spec.get("target_branch_name")
    if not branch:
        print("task_spec missing target_branch_name", file=sys.stderr)
        return 2
    print(f"target branch: {branch}", flush=True)

    with tempfile.TemporaryDirectory(prefix=f"coder-execute-{args.issue}-") as tmp:
        work = Path(tmp)
        print(f"== cloning {args.repo} into {work} ==", flush=True)
        repo_dir = clone_repo(args.repo, work)
        run(["git", "checkout", "-b", branch], cwd=repo_dir)

        print(f"== running executor (model={args.model}) ==", flush=True)
        prompt = build_executor_prompt(spec, repo_dir)
        raw, err = call_ollama(args.model, prompt, EXEC_TIMEOUT_SECONDS)
        if err:
            print(f"ollama error: {err}", file=sys.stderr)
            return 1

        parsed = parse_output(raw)

        if parsed["status"].startswith("BLOCKED") or not parsed["blocks"]:
            reason = parsed["status"] if parsed["status"].startswith("BLOCKED") else "executor produced no file blocks"
            body = (
                f"Executor returned: **{reason}**\n\n"
                f"Files emitted: {len(parsed['blocks'])}\n\n"
                f"Planner — please re-spec on this issue. "
                f"(Per liveness §22.5.2, > 2 plan↔execute cycles → STUCK.)"
            )
            run([
                "gh", "issue", "comment", str(args.issue),
                "--repo", args.repo, "--body", body,
            ])
            print(f"BLOCKED: {reason}. Comment posted on issue.", flush=True)
            return 1

        files_written = write_blocks(parsed["blocks"], repo_dir)
        print(f"wrote {len(files_written)} file(s):", flush=True)
        for f in files_written:
            print(f"  - {f}")

        cmd = (spec.get("acceptance_check") or {}).get("command", "")
        accept_rc = -1
        accept_stdout = ""
        accept_stderr = ""
        if cmd:
            print(f"== acceptance check ==\n  $ {cmd}", flush=True)
            try:
                ac = subprocess.run(
                    cmd, shell=True, cwd=repo_dir,
                    capture_output=True, text=True, timeout=ACCEPT_TIMEOUT_SECONDS,
                )
                accept_rc = ac.returncode
                accept_stdout = ac.stdout
                accept_stderr = ac.stderr
                print(f"  rc={accept_rc}", flush=True)
            except subprocess.TimeoutExpired:
                accept_stderr = f"timeout after {ACCEPT_TIMEOUT_SECONDS}s"
                print("  TIMEOUT", flush=True)
        else:
            print("(no acceptance_check command in task_spec)", flush=True)

        run(["git", "add", "-A"], cwd=repo_dir)
        violations = scope_guard_violations(spec, repo_dir)
        if violations:
            body = "Executor scope guard BLOCKED\n\n" + "\n".join(
                f"- {violation}" for violation in violations
            )
            run([
                "gh", "issue", "comment", str(args.issue),
                "--repo", args.repo, "--body", body,
            ])
            print("BLOCKED: Executor scope guard BLOCKED", flush=True)
            for violation in violations:
                print(f"  - {violation}", flush=True)
            return 1
        if not has_staged_changes(repo_dir):
            print("Executor produced no diff vs main. Aborting (no commit).", file=sys.stderr)
            return 1

        commit_msg = f"#{args.issue}: {issue.get('title', 'executor commit')}"
        run([
            "git",
            "-c", f"user.email={GIT_AUTHOR_EMAIL}",
            "-c", f"user.name={GIT_AUTHOR_NAME}",
            "commit", "-m", commit_msg,
        ], cwd=repo_dir)

        if args.dry_run:
            diff_stat = run(["git", "diff", "main", "--stat"], cwd=repo_dir, check=False).stdout
            print("== dry run — diff stat ==", flush=True)
            print(diff_stat)
            return 0 if accept_rc == 0 else 1

        print("== pushing branch ==", flush=True)
        run(["git", "push", "-u", "origin", branch], cwd=repo_dir, timeout=120)

        pr_body_lines = [
            f"Closes #{args.issue}",
            "",
            "## task_spec",
            "",
            "```json",
            json.dumps(spec, indent=2, default=str),
            "```",
            "",
            "## Acceptance check",
            "",
            f"- command: `{cmd or '(none)'}`",
            f"- exit code: **{accept_rc}**",
            "",
            "### stdout (tail)",
            "",
            "```",
            accept_stdout[-2000:] if accept_stdout else "(empty)",
            "```",
            "",
            "### stderr (tail)",
            "",
            "```",
            accept_stderr[-500:] if accept_stderr else "(empty)",
            "```",
            "",
            "## Universal output block",
            "",
            f"- What I did:        ran coder.execute on issue #{args.issue}",
            f"- What changed:      {len(files_written)} file(s): {files_written}",
            f"- Tests run:         `{cmd or '(none)'}` → rc={accept_rc}",
            f"- Risk:              {'low' if accept_rc == 0 else 'medium'}",
            "- Cost flags:        none",
            "- Decisions needed:  none",
            "- Heartbeat:         executor completed",
        ]
        pr_body = "\n".join(pr_body_lines)

        print("== opening PR ==", flush=True)
        pr_url = run([
            "gh", "pr", "create",
            "--repo", args.repo,
            "--base", "main",
            "--head", branch,
            "--title", f"#{args.issue}: {issue.get('title', '')}",
            "--body", pr_body,
        ], cwd=repo_dir, timeout=60).stdout.strip()
        print(f"PR: {pr_url}", flush=True)
        return 0 if accept_rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
