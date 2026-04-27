# Nightly Policy

The nightly agent improves the studio overnight. It is the most powerful agent (it can edit the system that runs it) and therefore the most carefully constrained.

## Default mode: report-only (Nightly v1)

- Reads ai-system files and product repo issue/PR metadata
- Generates a markdown report at `reports/nightly/YYYY-MM-DD.md`
- Anti-stall report at the top (per `policies/liveness-policy.md` §22.5.8)
- Emits no code changes, no PRs, no API calls beyond local

## Phased autonomy ladder

The nightly agent's permissions expand only after the prior level is stable.

| Level | What's allowed                                              | Anis enables when                       |
|-------|-------------------------------------------------------------|------------------------------------------|
| v1    | Reports only (no writes)                                    | Default at bootstrap                     |
| v2    | Create GitHub issues for improvements                       | After 7+ days of clean v1 reports        |
| v3    | Open PRs in `ai-system` only (prompts/policies/workflows)   | After eval harness gating is wired up    |
| v4    | Open low-risk PRs in product repos (docs/tests/lint only)   | After v3 has merged 5+ clean PRs         |

Auto-merge is **never** enabled by the nightly without explicit per-class Anis approval, regardless of level.

## Forbidden at every level

- Spending money / using paid APIs without approval
- Publishing / releasing
- Deploying
- Merging any PR (auto or manual)
- Deleting repos or branches
- Weakening branch protection or any policy
- Touching `policies/security-policy.md` or `policies/cost-policy.md` (proposing changes via PR is fine; merging them is not nightly's call)

## Required outputs of every nightly run

Every nightly report must include, in order:

1. **anti_stall_report** (top — see `policies/liveness-policy.md` §22.5.8)
2. What happened in the last 24h (commits, PRs, issues moved)
3. Blocked work (Waiting for Anis, STUCK)
4. Broken workflows / failing CI
5. Repeated agent mistakes (look for patterns)
6. Suggested improvements
7. Cost risks
8. Decisions needed from Anis
9. Proposed next-day priorities

## Eval gating (nightly v3+)

Any PR the nightly agent opens to `ai-system` triggers `evaluations/run_evals.py` in CI. The PR cannot merge if the eval pass rate drops vs. the current `main` baseline.

This makes the nightly self-improvement loop falsifiable. Without it, "improve the system" becomes a slow-motion regression engine.

## Budget

```yaml
nightly_budget:
  local_model: unlimited_within_machine
  codex: disabled_by_default
  codex_allowed_days: []                # Anis enables specific days
  max_codex_tasks_per_night: 1           # cap when allowed
  ask_before_using_codex: true           # always confirm
```
