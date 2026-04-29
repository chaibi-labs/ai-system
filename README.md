# ai-system

Control repo for Anis's Personal AI Dev Studio.

The studio builds personal software products end-to-end using:

- **Codex / GPT** (via ChatGPT subscription) — the senior engineer / brain. Plans, decomposes, reviews, debugs hard problems. Every task starts here.
- **Local models on Ollama** — the executors / hands. Run mechanical Codex-authored task specs (boilerplate, test stubs, single-file edits, mechanical refactors). Capability bar: "knows the language" — never asked to reason about the repo.
- **OpenClaw** — orchestrator and chat surface, with skills that route to the layers above.
- **GitHub Projects** — Kanban brain for the studio (issues, branches, PRs).
- **WSL2 + Docker** — local execution environment.

**Anis** is the CEO and final product decision-maker. Each product may also have a repo-scoped Product Owner agent that keeps the MVP pipeline moving and may merge eligible product PRs under `policies/github-policy.md`. The studio asks Anis for product direction, taste, branding, costs, publishing, and any irreversible action.

**Claude Code is not used in the runtime autonomous loop.** Claude was the bootstrap engineer that built this repo; once handed off, the system runs on Codex + local models + OpenClaw only.

## What this repo contains

```
agents/        Role definitions (yaml) for PM, Product Owner, Architect, Coder, Reviewer, QA, Ops, Design, Research, Nightly
prompts/       Per-role prompts that load on top of policies/universal.md
policies/      Operating rules: cost, github, release, security, liveness, session-bootstrap, codex usage
workflows/     Multi-agent flows (new-product, feature-development, figma-to-website, mobile-app, nightly)
templates/     Worked task_spec example, ADR template, PR template, product brief template
evaluations/   Regression suite — task_specs with known-good outcomes the local executor must pass
scripts/       Orchestration helpers (repo_health, nightly, codex_quota_probe, start_product, etc.)
decisions/     ADRs (Nygard format, sequentially numbered)
products/      Per-product config (created at runtime when Anis brings each product idea)
reports/       Nightly reports and one-off audits
memory/        Long-lived context the system rehydrates from on session bootstrap
.github/       PR template, issue templates, future CI workflows
```

## Operating principles

1. **Specifier-executor.** Codex emits a structured `task_spec` (paths, signatures, expected diff shape, acceptance check, out-of-scope, allowed_new_dependencies). Local model implements only what the spec says. If unclear → returns BLOCKED, planner re-plans. No guessing, no scope creep.
2. **Cost firewall.** No spending without explicit Anis approval (see `policies/cost-policy.md`).
3. **Liveness over silence.** Every agent action emits a progress event; tasks that stall enter the `STUCK` state visibly within a heartbeat window, not nightly (see `policies/liveness-policy.md`).
4. **State lives in the issue, not the session.** Every agent session bootstraps from the linked issue + latest task_spec + recent comments before its first action (see `policies/session-bootstrap.md`).
5. **Kill switch.** `~/.ai-system/HALT` pauses everything globally. Checked before any agent action — even before quota-burning bootstrap reads.

## Where to start

- New to the system? Read `README.md` (this file), then `policies/universal.md`, then `policies/liveness-policy.md`.
- Building a feature? `workflows/feature-development.yaml`.
- Starting a new product? Anis triggers `workflows/new-product.yaml`; the PM agent picks up.
- Things look stuck? Run `scripts/repo_health.py` and check the latest `reports/nightly/`.

## Source plan

The full architectural rationale lives in `README_personal_ai_dev_studio.md` at the top of the dev_team_setup folder. This repo is the implementation; that document is the design rationale.
