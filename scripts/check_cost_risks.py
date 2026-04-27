#!/usr/bin/env python3
"""
check_cost_risks.py — scans a diff for cost-risk indicators.

Heuristic, not exhaustive. Looks for:
  - new top-level entries in package.json / requirements.txt / pyproject.toml
  - usage of API key env vars (`*_API_KEY`)
  - imports from known paid SDKs
  - new GitHub Actions workflow with `runs-on: ubuntu-latest` (free, fine) vs.
    larger runners (cost)

Returns JSON listing flags with severity (info / warn / block).

Usage:
    python3 scripts/check_cost_risks.py <base-ref>..<head-ref>
    python3 scripts/check_cost_risks.py --staged

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


HALT_FILE = Path("~/.ai-system/HALT").expanduser()


PAID_SDK_PATTERNS = [
    re.compile(r"\bopenai\b", re.IGNORECASE),         # API-key usage
    re.compile(r"\banthropic\b", re.IGNORECASE),
    re.compile(r"\bsegment\b", re.IGNORECASE),
    re.compile(r"\bmixpanel\b", re.IGNORECASE),
    re.compile(r"\bamplitude\b", re.IGNORECASE),
    re.compile(r"\bdatadog\b", re.IGNORECASE),
    re.compile(r"\bsentry\b", re.IGNORECASE),         # has free tier; flag for review
    re.compile(r"\bauth0\b", re.IGNORECASE),
    re.compile(r"\bclerk\b", re.IGNORECASE),
    re.compile(r"\bsupabase/supabase-js\b", re.IGNORECASE),  # free tier exists
    re.compile(r"\bvercel\b", re.IGNORECASE),
]

API_KEY_PATTERN = re.compile(r"\b[A-Z][A-Z0-9_]+_API_KEY\b")


def halted() -> bool:
    return HALT_FILE.exists()


def get_diff(spec: str | None, staged: bool) -> str:
    if staged:
        cmd = ["git", "diff", "--cached"]
    elif spec:
        cmd = ["git", "diff", spec]
    else:
        cmd = ["git", "diff"]
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def scan(diff: str) -> list[dict]:
    flags: list[dict] = []

    # Only look at added lines
    added = [
        line[1:] for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    text = "\n".join(added)

    for m in API_KEY_PATTERN.finditer(text):
        flags.append({
            "severity": "block",
            "kind": "api_key_reference",
            "match": m.group(0),
            "note": "Implies pay-per-request usage. cost-policy.md forbids without explicit Anis approval.",
        })

    for pat in PAID_SDK_PATTERNS:
        m = pat.search(text)
        if m:
            flags.append({
                "severity": "warn",
                "kind": "paid_sdk_reference",
                "match": m.group(0),
                "note": "Paid SDK or service. Verify cost flag and free-tier coverage.",
            })

    if "package.json" in diff and ('"dependencies"' in diff or '"devDependencies"' in diff):
        flags.append({
            "severity": "info",
            "kind": "manifest_change",
            "match": "package.json",
            "note": "package.json modified — verify new entries are in task_spec.allowed_new_dependencies.",
        })

    if re.search(r"runs-on:\s*windows-2", diff) or re.search(r"runs-on:\s*macos-", diff):
        flags.append({
            "severity": "warn",
            "kind": "ci_runner",
            "match": "non-ubuntu runner",
            "note": "Non-ubuntu GitHub-hosted runners are billed at higher multiplier. Confirm minutes budget.",
        })

    return flags


def main() -> int:
    if halted():
        print(json.dumps({"halted": True}))
        return 0

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", nargs="?", help="git diff spec, e.g., main..HEAD")
    ap.add_argument("--staged", action="store_true")
    args = ap.parse_args()

    diff = get_diff(args.spec, args.staged)
    flags = scan(diff)

    severity_max = "info"
    for f in flags:
        if f["severity"] == "block":
            severity_max = "block"
            break
        if f["severity"] == "warn":
            severity_max = "warn"

    print(json.dumps({"verdict": severity_max, "flags": flags}, indent=2))
    return {"info": 0, "warn": 1, "block": 2}[severity_max]


if __name__ == "__main__":
    sys.exit(main())
