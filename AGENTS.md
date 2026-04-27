# AGENTS.md

This repo is maintained by Anis's personal AI dev studio. Every agent that touches this repo (and any product repo it spawns) operates under these rules.

## Universal rules

1. Work through GitHub issues, branches, and PRs.
2. Never push directly to `main`.
3. Never spend money or activate any paid service without explicit Anis approval.
4. Never publish (App Store, Play Store, public web launch) without Anis approval.
5. Never create external accounts.
6. Never commit secrets. Secrets live in `~/.ai-system/secrets/`, not in any repo.
7. Ask Anis for product, taste, inspiration, branding, pricing, and cost decisions.
8. Prefer local models for execution; reserve Codex/GPT for planning, review, and hard reasoning.
9. Keep changes small and reviewable. One concern per PR.
10. Before any action, complete the session bootstrap reads (see `policies/session-bootstrap.md`).
11. Before any action, check the kill switch (`~/.ai-system/HALT`). If present → exit cleanly.

## Decision gates (require Anis)

- Paid APIs / SaaS / hosting / domains / auth providers / analytics
- Apple Developer Program enrollment, EAS paid builds, App/Play Store submission
- Major rewrites or stack changes
- Brand / name / pricing / public launch
- Privacy / legal decisions
- Any quota-impacting nightly Codex use

## Output style for every agent action

Always include:
- What you did
- What changed (files, commits, PRs)
- What needs review
- What decisions are needed from Anis (if any)
- What costs may be involved (if any)
- Heartbeat / progress event for liveness tracking

## Forbidden

- Silent spending
- Silent publishing
- Silent account creation
- Silent weakening of safety rules
- Committing secrets
- Bypassing GitHub PR workflow
- Adding dependencies not listed in `task_spec.allowed_new_dependencies` (return BLOCKED instead)

For the full rule set and rationale, see `policies/universal.md`.
