---
name: summarize-prs
description: 'List open PRs across all chaibi-labs repos and summarize each: title, age, CI status, review state, what task_spec it implements (if any), blockers. Read-only. NOT for merging.'
metadata:
  openclaw:
    emoji: "📊"
    requires:
      anyBins: ["gh"]
---

# /summarize-prs — PR overview

Trigger: `/summarize-prs` (no args) or `/summarize-prs <repo>` to scope to one repo.

## What you do

```bash
[[ -f /home/anis/.ai-system/HALT ]] && { echo "HALTED"; exit 0; }
# GH_TOKEN/GITHUB_TOKEN are injected by systemd from ~/.ai-system/secrets/.env
# at OpenClaw daemon start (see ~/.config/systemd/user/openclaw-gateway.service.d/
# secrets.conf). Agents inherit them via the process tree — no agent reads the
# secrets file directly, honoring policies/security-policy.md.
```

For each open PR across all `chaibi-labs/*` repos (or just one if scoped):

```bash
gh search prs --owner chaibi-labs --state open --json url,title,number,repository,createdAt,author,labels
```

Then for each PR:

```bash
gh pr view <ref> --json title,body,statusCheckRollup,reviewDecision,additions,deletions,files,labels,baseRefName,headRefName,createdAt,updatedAt
```

Extract from each:
- task_spec presence (look for `task_spec:` block in body)
- CI status (green / red / pending / unknown)
- Review state (approved / changes-requested / pending review)
- Age (days since createdAt)
- Cost flags from PR body (none / list)
- Blockers if review left any

## Output format

```
Open PRs across chaibi-labs (N total)

[chaibi-labs/<repo>#<N>] <title>
  Author:        <user>
  Age:           <N> days
  CI:            green | red | pending
  Review:        approved | changes-requested | pending
  task_spec:     yes | no (planner missed it?)
  Cost flags:    none | <list>
  Blockers:      <count>
  URL:           <url>

[chaibi-labs/<repo>#<N>] …

Summary:
  Approved + green:    <count>  ← Anis can merge
  Pending review:       <count>
  Changes requested:    <count>
  Failing CI:           <count>  ← cascade-halt risk per liveness §22.5.7
```

## When to flag liveness issues

If any PR shows red CI on `main`-targeted branch in an active product, surface a cascade-halt warning at the top of the output — per `policies/liveness-policy.md` §22.5.7, all `coder.execute` work for that repo should pause until the fix lands.
