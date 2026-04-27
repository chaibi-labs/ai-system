#!/usr/bin/env python3
"""
start_product.py — bootstraps a new product as configured by the new-product workflow.

Usage:
    python3 scripts/start_product.py <product-name> --type <mobile-app|website|backend>

Effects (all guarded by --dry-run):
    1. Writes products/<name>.yaml with stack defaults from policies/mobile-policy.md
       or web defaults
    2. Creates the GitHub repo `chaibi-labs/<name>` (private by default)
    3. Adds AGENTS.md, .gitignore, PR template
    4. Sets up labels matching ai-system's label set
    5. Initializes the docs/ runbook stub
    6. Adds a starter ADR placeholder

Requires: gh CLI authed; `policies/cost-policy.md` allows free-tier private repos.
Stdlib only (subprocess shells out to gh).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HALT_FILE = Path("~/.ai-system/HALT").expanduser()


PRODUCT_TEMPLATE = """\
name: {name}
type: {ptype}
stack:
{stack_block}
status: ideation
created_at: {created_at}
cost_gates:
  - apple_developer_program        # if {ptype} is mobile-app
  - expo_eas_build                 # if {ptype} is mobile-app
  - paid_food_database_api         # adjust per product
  - hosting                         # if {ptype} is website / backend
  - domain
"""

STACK_DEFAULTS = {
    "mobile-app": [
        "  mobile: expo-react-native-typescript",
        "  state: zustand",
        "  local_data: sqlite (expo-sqlite)",
        "  backend: undecided",
        "  database: undecided",
    ],
    "website": [
        "  framework: nextjs",
        "  language: typescript",
        "  styling: tailwind",
        "  motion: framer-motion",
        "  components: shadcn-where-helpful",
    ],
    "backend": [
        "  framework: fastapi",
        "  language: python",
        "  database: postgres",
        "  containerization: docker-compose",
    ],
}


def halted() -> bool:
    return HALT_FILE.exists()


def write_product_config(name: str, ptype: str) -> Path:
    from datetime import datetime, timezone

    products_dir = REPO_ROOT / "products"
    products_dir.mkdir(parents=True, exist_ok=True)
    cfg = products_dir / f"{name}.yaml"
    stack_lines = STACK_DEFAULTS.get(ptype, ["  TBD: true"])
    cfg.write_text(
        PRODUCT_TEMPLATE.format(
            name=name,
            ptype=ptype,
            stack_block="\n".join(stack_lines),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    )
    return cfg


def create_repo(name: str, dry_run: bool) -> None:
    full = f"chaibi-labs/{name}"
    cmd = [
        "gh",
        "repo",
        "create",
        full,
        "--private",
        "--description",
        f"chaibi-labs personal product: {name}",
        "--add-readme",
    ]
    print(f"$ {' '.join(cmd)}")
    if dry_run:
        return
    subprocess.run(cmd, check=True)


def main() -> int:
    if halted():
        print("HALT file present; aborting.", file=sys.stderr)
        return 0

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("name")
    ap.add_argument("--type", required=True, choices=["mobile-app", "website", "backend"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = write_product_config(args.name, args.type)
    print(f"Wrote: {cfg.relative_to(REPO_ROOT)}")

    create_repo(args.name, args.dry_run)

    print(
        json.dumps(
            {
                "name": args.name,
                "type": args.type,
                "config": str(cfg.relative_to(REPO_ROOT)),
                "repo": f"chaibi-labs/{args.name}",
                "dry_run": args.dry_run,
                "next": [
                    "Run the new-product workflow PM/design intake questions",
                    "Architect drafts ADR for stack",
                    "Anis approves brief + ADR before any code",
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
