#!/usr/bin/env python3
"""
create_issue_batch.py — creates a batch of GitHub issues from a YAML manifest.

Used by the PM agent to seed the first 10 issues for a new product, and by the
nightly agent (v2+) to file improvement issues.

Manifest format (YAML):

    repo: chaibi-labs/<repo>
    project: <project number, e.g. 1>
    issues:
      - title: "Define product brief"
        body: "..."
        labels: ["agent:pm", "type:chore", "decision:anis"]
        agent_field: pm
        priority_field: P1 (high)
      - ...

Stdlib only (no PyYAML). The "YAML" we accept here is the strict subset
used by our manifests — we parse it as JSON-with-comment-tolerant if you save
as .json, otherwise we shell out to `yq` if installed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


HALT_FILE = Path("~/.ai-system/HALT").expanduser()


def halted() -> bool:
    return HALT_FILE.exists()


def parse_manifest(path: Path) -> dict:
    """Accept either .json or .yaml (yaml requires `yq` available)."""
    if path.suffix in (".json",):
        return json.loads(path.read_text())
    # Try yq
    try:
        out = subprocess.run(
            ["yq", "-o", "json", str(path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        return json.loads(out)
    except FileNotFoundError:
        print(
            "yq not installed and manifest is not JSON. Install yq or convert manifest.",
            file=sys.stderr,
        )
        sys.exit(2)


def create_issue(repo: str, issue: dict, dry_run: bool) -> str | None:
    cmd = [
        "gh",
        "issue",
        "create",
        "--repo",
        repo,
        "--title",
        issue["title"],
        "--body",
        issue.get("body", ""),
    ]
    for lab in issue.get("labels", []):
        cmd += ["--label", lab]

    print(f"$ {' '.join(repr(c) for c in cmd)}")
    if dry_run:
        return None
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
    return out


def main() -> int:
    if halted():
        print("HALT file present; aborting.", file=sys.stderr)
        return 0

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    manifest = parse_manifest(args.manifest)
    repo = manifest["repo"]
    issues = manifest.get("issues", [])

    created = []
    for i in issues:
        url = create_issue(repo, i, args.dry_run)
        if url:
            created.append({"title": i["title"], "url": url})

    print(json.dumps({"repo": repo, "created": created, "dry_run": args.dry_run}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
