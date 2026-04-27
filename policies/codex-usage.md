# Codex Usage Policy

Codex is the premium senior engineer layer. It is the **brain** of the specifier-executor model: it plans, decomposes work into `task_spec`s for local executors, reviews diffs, and handles hard reasoning. Every task flows through Codex first.

## Codex's throughput is the system's bottleneck

Subscription quota is finite per rolling window. Treat every Codex call as a budget item.

- The orchestrator runs `scripts/codex_quota_probe.py` before every planner session and writes state to `~/.ai-system/quota_state.json`.
- States: `green` (>50% remaining) → normal · `yellow` (20-50%) → critical-path only, defer nightly · `red` (<20%) → planner-draft mode, no executor runs · `exhausted` → report-only.
- See `policies/liveness-policy.md` §"Quota-aware degradation".

## Use local models first for

- Drafting boilerplate from a defined skeleton
- Single-file edits with a fully specified diff shape
- Writing test stubs against given signatures
- Mechanical refactors (rename, move, reformat)
- Filling doc templates from a given outline
- Transcribing logs/output into a specified summary structure

## Use Codex (escalate) for

- Architecture and stack choices
- Decomposing tickets into local-executable specs
- Hard debugging (multi-file root-cause)
- Difficult implementation that crosses files
- Final code review before merge
- Security-sensitive code or review
- Mobile build / release planning
- Complex Figma-to-code interpretation
- Anything where the local model would have to guess

## Codex authentication

Codex authenticates via **ChatGPT login** (subscription-based), not API key. The presence of any `OPENAI_API_KEY` on disk is a configuration error — it implies pay-per-request usage which `policies/cost-policy.md` forbids.

If Codex prompts for re-auth, Anis re-authenticates manually. Agents do not script around the auth prompt.

## Codex approval modes

Standard rules:

```
Suggest mode (default for unfamiliar repos):
- code review
- planning
- risky changes
- any work in a repo without tests

Auto Edit:
- safe repetitive edits
- doc-only changes
- test additions for existing functions
- small refactors with clear scope

Full Auto:
- only inside a clean git branch
- only when tests exist and pass before edits
- only when no secrets are accessible
- never for publishing / deployment / cost actions
```

## Ask Anis before

- Long-running Codex sessions (>30 min wall clock)
- Parallel Codex agents
- Cloud Codex delegation
- External SaaS usage
- Account creation
- Publishing
- Payment or paid-quota usage

## Hard rules

- Codex does not commit secrets.
- Codex does not push directly to `main`.
- Codex does not approve its own PRs (the reviewer agent runs separately, even if it ultimately routes to Codex too).
- Codex does not enable `auto-merge` for any PR class without explicit Anis approval.
