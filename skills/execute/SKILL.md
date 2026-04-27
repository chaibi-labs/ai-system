---
name: execute
description: 'Run the Coder *executor* (local model, qwen2.5-coder:14b) against a task_spec attached to a GitHub issue. Pulls the latest task_spec from the issue body or comments, clones the target repo, creates the target branch, runs the executor, runs acceptance_check, and opens a PR. NOT for planning — use /plan first to produce a task_spec. NOT for review or merge.'
metadata:
  openclaw:
    emoji: "🛠️"
    requires:
      anyBins: ["python3", "ollama", "gh", "yq", "git"]
---

# /execute — Coder executor stage

Trigger: `/execute <issue-ref>` where `<issue-ref>` is `#N` (defaults to `chaibi-labs/ai-system`) or `chaibi-labs/<repo>#N`.

Optional flag: `--dry-run` (run executor + show diff stat, no push, no PR).

## Pre-action checks

1. `[[ -f /home/anis/.ai-system/HALT ]] && exit 0`
2. The executor uses the **local** model on Ollama, so it does NOT burn Codex quota. The follow-up reviewer / planner calls do, so still respect quota state if you trigger them.

## What you do

```bash
export $(grep -v '^#' /home/anis/.ai-system/secrets/.env | xargs)
cd /home/anis/src/ai-system
git pull --ff-only
python3 scripts/coder_execute.py <repo> <issue-number>
```

Default repo is `chaibi-labs/ai-system` if the user just gives `#N`.

## What the script does

1. Fetches the issue via `gh issue view`.
2. Extracts the `task_spec` from the issue body (preferred) or the latest comment with a ```yaml task_spec: ... ``` block.
3. Clones the target repo to a fresh `/tmp/coder-execute-<N>-<rand>/` (never touches Anis's working clone).
4. Creates the `task_spec.target_branch_name` branch.
5. Calls `qwen2.5-coder:14b` via the Ollama HTTP API with the task_spec + current repo file tree + strict file-block output instructions.
6. Parses `=== BEGIN FILE: <path> === ... === END FILE: <path> ===` blocks and writes them into the working tree.
7. If the executor returned `STATUS: BLOCKED ...` or emitted no file blocks → posts a comment on the issue, no PR opened.
8. Otherwise: runs `task_spec.acceptance_check`, captures actual stdout/stderr, commits with `DasGewuerz` author, pushes the branch, opens a PR with the task_spec + acceptance output + universal output block.

## Refusal cases

- task_spec missing on the issue → tell user to run `/plan #N` first
- `task_spec.target_branch_name` missing → planner error; comment on issue, don't proceed
- HALT switch active → exit cleanly
- ollama unreachable → fail with a clear error

## Output to user

```
Issue:       chaibi-labs/<repo>#<N>  ·  <title>
Source:      task_spec found in <body | comment-id>
Branch:      <target_branch_name>
Files:       <count>  (or BLOCKED — comment posted on issue)
Acceptance:  rc=<N>  (pass | fail)
PR:          <url>  (or — if BLOCKED or dry-run, none)
Status:      DONE | BLOCKED
Heartbeat:   executor completed
```

## Liveness

Per `policies/liveness-policy.md` §22.5.2, more than **2** plan↔execute cycles for the same task should escalate to STUCK. This skill itself does not enforce the count — that's the planner's job. If `/execute` returns BLOCKED, the next `/plan` invocation on the same issue should check how many BLOCKED comments already exist and refuse to plan a third time without Anis input.
