---
name: plan
description: 'Run the Coder *planner* (Codex) on a GitHub issue and emit a structured task_spec the local executor can implement mechanically. Use when an issue is in Spec Needed or has been reopened with a BLOCKED comment. NOT for actually writing code (that is the executor stage). Output: a task_spec YAML posted as an issue comment + the issue moved from Spec Needed to Ready.'
metadata:
  openclaw:
    emoji: "📋"
    requires:
      anyBins: ["codex", "gh"]
---

# /plan — Coder planner

Trigger: `/plan <issue-ref>` where `<issue-ref>` is `#N` (defaults to `chaibi-labs/ai-system`) or `chaibi-labs/<repo>#N`.

## Pre-action checks

1. `[[ -f /home/anis/.ai-system/HALT ]] && exit 0`
2. `python3 /home/anis/src/ai-system/scripts/codex_quota_probe.py --quiet`
3. Read `/home/anis/.ai-system/quota_state.json`. If `state == exhausted` → tell user, exit. If `state == red` and not critical-path → tell user the task is deferred.

## What you do

```bash
# GH_TOKEN/GITHUB_TOKEN are injected by systemd from ~/.ai-system/secrets/.env
# at OpenClaw daemon start (see ~/.config/systemd/user/openclaw-gateway.service.d/
# secrets.conf). Agents inherit them via the process tree — no agent reads the
# secrets file directly, honoring policies/security-policy.md.
cd /home/anis/src/ai-system
git pull --ff-only
```

1. Read the linked issue:
   ```bash
   gh issue view <ref> --json number,title,body,labels,comments
   ```
2. If the issue has zero comments and no prior task_spec → initial planning mode.
   If the latest comment is `BLOCKED:` → re-plan with the BLOCKED reason as input.

3. Load `prompts/coder-planner.md` and `policies/universal.md`. Use Codex (`codex exec`) with those as system context, the issue body as user input.

4. Codex must produce a task_spec following `templates/task_spec_example.yaml`. Mandatory fields:
   - target_branch_name
   - files_to_create_or_edit (exact paths)
   - function_signatures (quotable)
   - expected_diff_shape (per file)
   - test_files_and_cases
   - acceptance_check (one command + one outcome)
   - out_of_scope (mandatory)
   - allowed_new_dependencies (mandatory if touching a manifest)
   - budget

5. Post the task_spec as a comment on the issue:
   ```bash
   gh issue comment <ref> --body-file <(cat task_spec.yaml | sed 's/^/    /')
   ```
   (Or as a code block; mind YAML indentation.)

6. Move the issue from `Spec Needed` → `Ready` on Project #1.

7. Append a session record to `~/.ai-system/codex_sessions.log`:
   ```bash
   echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)\tplan\t<issue-ref>" >> ~/.ai-system/codex_sessions.log
   ```

## When to refuse / ask Anis instead

- Issue is ambiguous about user-facing behavior → comment back with the specific question, leave issue in `Spec Needed`. Do NOT guess.
- Issue is too large for one spec → decompose into N child issues, link as parent/child, return a list of new issue numbers.
- Issue requires a stack/cost decision → tag `decision:anis`, comment with the decision needed, leave in `Waiting for Anis`.

## Liveness budget

Per `policies/liveness-budgets.yaml` defaults:
- max_codex_calls_per_task: 8
- max_plan_attempts: 2 (more than 2 plan↔execute cycles for one task = STUCK)

## Output to user

```
Issue:    chaibi-labs/ai-system#<N>
Action:   plan emitted | BLOCKED: <reason> | decomposed into [#A, #B, ...] | needs Anis: <decision>
Branch:   <target_branch_name>
Files:    <count>
Codex:    <calls used in this run> / 8 budget
Quota:    <green/yellow/red/exhausted> · <remaining_pct>%
```
