#!/usr/bin/env python3
"""
po_github.py — validate and use repo-scoped Product Owner GitHub credentials.

Secrets live outside the repo at:
  ~/.ai-system/secrets/<po_agent>.env

Expected env file keys:
  GITHUB_TOKEN=...
  GITHUB_USER=<machine-user-login>
  GITHUB_REPO=owner/repo

This script never prints tokens.

Usage:
  python3 scripts/po_github.py validate pregnancy-food-checker
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - repo environment should include PyYAML
    yaml = None


HALT_FILE = Path("~/.ai-system/HALT").expanduser()
PRODUCTS_DIR = Path("products")
SECRETS_DIR = Path("~/.ai-system/secrets").expanduser()


class PoConfigError(RuntimeError):
    pass


def halted() -> bool:
    return HALT_FILE.exists()


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_product(product_name: str) -> dict[str, Any]:
    if yaml is None:
        raise PoConfigError("PyYAML is required to read product config")
    product_path = PRODUCTS_DIR / f"{product_name}.yaml"
    if not product_path.exists():
        raise PoConfigError(f"product config not found: {product_path}")
    data = yaml.safe_load(product_path.read_text()) or {}
    if not isinstance(data, dict):
        raise PoConfigError(f"product config must be a mapping: {product_path}")
    return data


def product_secret_path(product: dict[str, Any]) -> Path:
    po_agent = product.get("po_agent")
    if not po_agent:
        raise PoConfigError("product has no po_agent")
    configured = product.get("po_secret_env")
    if configured:
        return Path(str(configured)).expanduser()
    return SECRETS_DIR / f"{po_agent}.env"


def github_get(token: str, path_or_url: str) -> Any:
    url = path_or_url if path_or_url.startswith("https://") else f"https://api.github.com{path_or_url}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise PoConfigError(f"GitHub API {exc.code} for {url}: {detail}") from exc


def visible_chaibi_labs_repos(token: str) -> list[str]:
    repos = github_get(token, "/user/repos?per_page=100&affiliation=collaborator,organization_member,owner")
    if not isinstance(repos, list):
        raise PoConfigError("unexpected /user/repos response")
    return sorted(
        repo.get("full_name", "")
        for repo in repos
        if str(repo.get("full_name", "")).startswith("chaibi-labs/")
    )


def validate(product_name: str) -> dict[str, Any]:
    product = load_product(product_name)
    repo = product.get("repo")
    po_agent = product.get("po_agent")
    if not repo:
        raise PoConfigError("product has no repo")

    secret_path = product_secret_path(product)
    if not secret_path.exists():
        raise PoConfigError(f"PO secret file missing: {secret_path}")

    mode = stat.S_IMODE(secret_path.stat().st_mode)
    env = load_env_file(secret_path)
    token = env.get("GITHUB_TOKEN")
    configured_user = env.get("GITHUB_USER")
    configured_repo = env.get("GITHUB_REPO")
    if not token:
        raise PoConfigError(f"GITHUB_TOKEN missing from {secret_path}")
    if configured_repo != repo:
        raise PoConfigError(f"GITHUB_REPO mismatch: expected {repo}, got {configured_repo}")

    user = github_get(token, "/user")
    token_user = user.get("login")
    if configured_user and configured_user != token_user:
        raise PoConfigError(f"GITHUB_USER mismatch: expected {configured_user}, got {token_user}")

    repo_info = github_get(token, f"/repos/{repo}")
    permissions = repo_info.get("permissions", {})
    visible_repos = visible_chaibi_labs_repos(token)

    expected_visible = [repo]
    verdict = "pass"
    failures: list[str] = []
    if mode != 0o600:
        verdict = "fail"
        failures.append(f"secret file mode must be 600, got {oct(mode)}")
    if not permissions.get("push"):
        verdict = "fail"
        failures.append("token lacks push/write permission")
    if permissions.get("admin"):
        verdict = "fail"
        failures.append("token has admin permission; PO must not be admin")
    if visible_repos != expected_visible:
        verdict = "fail"
        failures.append(f"token can see unexpected chaibi-labs repos: {visible_repos}")

    return {
        "verdict": verdict,
        "product": product_name,
        "repo": repo,
        "po_agent": po_agent,
        "secret_file": str(secret_path),
        "secret_mode": oct(mode),
        "token_user": token_user,
        "permissions": {
            "admin": bool(permissions.get("admin")),
            "push": bool(permissions.get("push")),
            "triage": bool(permissions.get("triage")),
            "pull": bool(permissions.get("pull")),
        },
        "visible_chaibi_labs_repos": visible_repos,
        "failures": failures,
    }


def main() -> int:
    if halted():
        print(json.dumps({"halted": True, "reason": str(HALT_FILE)}))
        return 0

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate_parser = sub.add_parser("validate", help="validate a product PO token boundary")
    validate_parser.add_argument("product", help="product config name, e.g. pregnancy-food-checker")
    args = parser.parse_args()

    try:
        if args.command == "validate":
            result = validate(args.product)
            print(json.dumps(result, indent=2))
            return 0 if result["verdict"] == "pass" else 1
    except PoConfigError as exc:
        print(json.dumps({"verdict": "fail", "error": str(exc)}, indent=2))
        return 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
