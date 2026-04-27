#!/usr/bin/env python3
"""
safe_git_status.py — read-only git status for an agent.

Returns a structured JSON view of the working tree without ever mutating it.
Refuses to run if the kill switch (~/.ai-system/HALT) is set. Stdlib only.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


HALT_FILE = Path("~/.ai-system/HALT").expanduser()


def halted() -> bool:
    return HALT_FILE.exists()


def run(cmd: list[str], cwd: Path | None = None) -> str:
    return subprocess.run(
        cmd, cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def main() -> int:
    if halted():
        print(json.dumps({"halted": True, "reason": str(HALT_FILE)}))
        return 0

    cwd = Path.cwd()
    try:
        repo_root = run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    except subprocess.CalledProcessError:
        print(json.dumps({"error": "not a git repo", "cwd": str(cwd)}))
        return 1

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=Path(repo_root))
    porcelain = run(["git", "status", "--porcelain=v1"], cwd=Path(repo_root))

    untracked = []
    modified = []
    staged = []
    for line in porcelain.splitlines():
        if not line:
            continue
        x, y = line[0], line[1]
        path = line[3:]
        if x == "?":
            untracked.append(path)
        else:
            if x != " ":
                staged.append(path)
            if y != " " and y != "?":
                modified.append(path)

    ahead_behind_raw = run(
        [
            "git",
            "rev-list",
            "--left-right",
            "--count",
            "HEAD...@{upstream}",
        ],
        cwd=Path(repo_root),
    ) if has_upstream(Path(repo_root)) else "0\t0"
    ahead, behind = ahead_behind_raw.split("\t") if "\t" in ahead_behind_raw else ("0", "0")

    print(
        json.dumps(
            {
                "halted": False,
                "repo_root": repo_root,
                "branch": branch,
                "ahead": int(ahead),
                "behind": int(behind),
                "untracked": untracked,
                "modified": modified,
                "staged": staged,
            },
            indent=2,
        )
    )
    return 0


def has_upstream(repo_root: Path) -> bool:
    try:
        subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "@{upstream}"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


if __name__ == "__main__":
    sys.exit(main())
