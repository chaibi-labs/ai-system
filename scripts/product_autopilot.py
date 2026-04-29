#!/usr/bin/env python3
"""
product_autopilot.py — conservative one-issue product autopilot coordinator.

This script does not bypass the studio workflow. It selects one unblocked issue for
an assigned product, builds the exact PO-worker task prompt, and optionally claims
the issue with an autopilot comment.

It is intentionally one issue at a time. The worker still uses normal GitHub flow:
issue -> branch -> PR -> local tests -> CI -> PO gate comment -> PO-token merge.

Usage:
  python3 scripts/product_autopilot.py pregnancy-food-checker --dry-run
  python3 scripts/product_autopilot.py pregnancy-food-checker --issue 37 --dry-run
  python3 scripts/product_autopilot.py pregnancy-food-checker --claim
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from po_github import PoConfigError, github_get, halted, load_env_file, load_product, product_secret_path, validate


BLOCKING_LABELS = {
    "decision:anis",
    "cost:approval-required",
    "blocked",
    "status:blocked",
    "stuck",
    "question",
    "wontfix",
    "invalid",
    "duplicate",
}

PREFERRED_LABEL_ORDER = ["priority:P1", "priority:P2", "priority:P3"]


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    body: str
    labels: tuple[str, ...]
    html_url: str
    created_at: str
    updated_at: str

    @property
    def is_blocked(self) -> bool:
        return bool(set(self.labels) & BLOCKING_LABELS)

    @property
    def priority_rank(self) -> int:
        for idx, label in enumerate(PREFERRED_LABEL_ORDER):
            if label in self.labels:
                return idx
        return len(PREFERRED_LABEL_ORDER)


def github_post(token: str, path: str, payload: dict[str, Any]) -> Any:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise PoConfigError(f"GitHub API {exc.code} for {url}: {detail}") from exc


def load_po_token(product: dict[str, Any]) -> str:
    secret_path = product_secret_path(product)
    env = load_env_file(secret_path)
    token = env.get("GITHUB_TOKEN")
    if not token:
        raise PoConfigError(f"GITHUB_TOKEN missing from {secret_path}")
    return token


def parse_issue(raw: dict[str, Any]) -> Issue:
    return Issue(
        number=int(raw["number"]),
        title=str(raw.get("title", "")),
        body=str(raw.get("body") or ""),
        labels=tuple(label.get("name", "") for label in raw.get("labels", [])),
        html_url=str(raw.get("html_url", "")),
        created_at=str(raw.get("created_at", "")),
        updated_at=str(raw.get("updated_at", "")),
    )


def list_open_issues(token: str, repo: str) -> list[Issue]:
    query = urllib.parse.urlencode({"state": "open", "per_page": 100})
    raw_issues = github_get(token, f"/repos/{repo}/issues?{query}")
    if not isinstance(raw_issues, list):
        raise PoConfigError("unexpected issues response")
    issues = [parse_issue(item) for item in raw_issues if "pull_request" not in item]
    return sorted(issues, key=lambda issue: (issue.priority_rank, issue.created_at, issue.number))


def choose_issue(issues: list[Issue], issue_number: int | None = None) -> Issue | None:
    ordered = sorted(issues, key=lambda issue: (issue.priority_rank, issue.created_at, issue.number))
    if issue_number is not None:
        for issue in ordered:
            if issue.number == issue_number:
                return None if issue.is_blocked else issue
        return None
    for issue in ordered:
        if not issue.is_blocked:
            return issue
    return None


def build_worker_prompt(product_name: str, product: dict[str, Any], issue: Issue) -> str:
    repo = product["repo"]
    return f"""You are acting as the repo-scoped Product Owner for {repo}, assigned to product {product_name}. Run this issue end-to-end with minimal parent intervention.

Issue: {issue.html_url}
Title: {issue.title}
Labels: {', '.join(issue.labels) or '(none)'}

Hard requirements:
- Do not print or expose secrets.
- Validate PO credential boundary before merge using: python3 /tmp/ai-system-po/scripts/po_github.py validate {product_name}
- Use normal GitHub flow: inspect issue, create branch, commit, PR, local tests, CI, PO gate comment, merge with PO token only if gates pass.
- Use the PO token only by sourcing ~/.ai-system/secrets/{product.get('po_agent')}.env locally; never echo it.
- Keep change small and one-concern.
- Stop and return BLOCKED if the issue requires cost, API tokens/secrets, Render/provider setup, privacy/legal/product direction, public release, branch protection, or any exception to PO merge gates.
- Add or update regression tests for the behavior.
- Run the relevant focused test, npm test, and npm run build locally before PR when this is the Next.js product.
- Wait for GitHub CI to pass before PO merge.
- After merge, verify PR merged by the PO token user and linked issue closed.

PO merge gates:
- assigned repo: pass/fail
- reviewer: pass/fail
- CI/checks: pass/fail
- cost/privacy/release gates: pass/fail
- unresolved blockers: pass/fail
- one-concern diff: pass/fail

Final response back to parent must include: issue URL, PR URL, merge status, tests run, risk, cost flags, decisions needed, heartbeat."""


def claim_issue(token: str, repo: str, issue: Issue) -> str:
    body = (
        "Autopilot picked this issue for one-issue PO execution. "
        "It will stop and report BLOCKED if cost, secrets, provider setup, privacy/legal, "
        "product direction, release, branch protection, or merge-gate exceptions are needed."
    )
    response = github_post(token, f"/repos/{repo}/issues/{issue.number}/comments", {"body": body})
    return str(response.get("html_url", ""))


def run(product_name: str, issue_number: int | None, claim: bool) -> dict[str, Any]:
    validation = validate(product_name)
    if validation["verdict"] != "pass":
        return {"verdict": "blocked", "reason": "po credential validation failed", "validation": validation}

    product = load_product(product_name)
    repo = str(product["repo"])
    token = load_po_token(product)
    issues = list_open_issues(token, repo)
    issue = choose_issue(issues, issue_number)
    if issue is None:
        return {
            "verdict": "blocked",
            "reason": "no unblocked matching issue",
            "open_issues": [
                {"number": item.number, "title": item.title, "labels": list(item.labels), "blocked": item.is_blocked}
                for item in issues
            ],
        }

    claim_url = claim_issue(token, repo, issue) if claim else None
    return {
        "verdict": "ready",
        "product": product_name,
        "repo": repo,
        "issue": {
            "number": issue.number,
            "title": issue.title,
            "url": issue.html_url,
            "labels": list(issue.labels),
        },
        "claim_comment": claim_url,
        "worker_prompt": build_worker_prompt(product_name, product, issue),
    }


def main() -> int:
    if halted():
        print(json.dumps({"halted": True, "reason": str(Path("~/.ai-system/HALT").expanduser())}, indent=2))
        return 0

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("product", help="product config name, e.g. pregnancy-food-checker")
    parser.add_argument("--issue", type=int, help="specific issue number to run instead of selecting next unblocked issue")
    parser.add_argument("--claim", action="store_true", help="post an autopilot claim comment to the selected issue")
    parser.add_argument("--dry-run", action="store_true", help="do not claim the issue; print selected issue and worker prompt")
    args = parser.parse_args()

    try:
        result = run(args.product, args.issue, claim=args.claim and not args.dry_run)
    except PoConfigError as exc:
        print(json.dumps({"verdict": "blocked", "error": str(exc)}, indent=2))
        return 1

    print(json.dumps(result, indent=2))
    return 0 if result.get("verdict") == "ready" else 1


if __name__ == "__main__":
    sys.exit(main())
