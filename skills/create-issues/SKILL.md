---
name: create-issues
description: 'Batch-create GitHub issues from a YAML/JSON manifest. Used by the PM agent to seed the first 10 issues for a new product, and by the nightly agent (v2+) to file improvement issues. NOT for free-form single issues — use `gh issue create` for those.'
metadata:
  openclaw:
    emoji: "📝"
    requires:
      anyBins: ["python3", "gh", "yq"]
---

# /create-issues — Batch issue creator

Trigger: `/create-issues <manifest-path>` where `<manifest-path>` is a path to a YAML or JSON manifest readable from WSL (e.g., a path under `/home/anis/src/ai-system/` or `/tmp/`).

Or paste the manifest body inline; the skill will write it to `/tmp/issues.yaml` and run from there.

## Manifest format

```yaml
repo: chaibi-labs/<repo>
project: 1                  # optional; defaults to chaibi-labs Project #1
issues:
  - title: "Define product brief"
    body: |
      What this issue is about, in 2-4 sentences.

      Acceptance: …
    labels: ["agent:pm", "type:chore", "decision:anis"]
    agent_field: pm           # optional Project field value
    priority_field: P1 (high) # optional
  - …
```

## What you do

```bash
[[ -f /home/anis/.ai-system/HALT ]] && { echo "HALTED"; exit 0; }
# GH_TOKEN/GITHUB_TOKEN are injected by systemd from ~/.ai-system/secrets/.env
# at OpenClaw daemon start (see ~/.config/systemd/user/openclaw-gateway.service.d/
# secrets.conf). Agents inherit them via the process tree — no agent reads the
# secrets file directly, honoring policies/security-policy.md.
cd /home/anis/src/ai-system
git pull --ff-only
python3 scripts/create_issue_batch.py <manifest-path>
```

If `--dry-run` is passed, the script prints the gh commands it WOULD run without creating anything. Use this first when in doubt.

## Pre-flight checks

- `repo` exists and Anis can write to it (the token has `repo` scope)
- All `labels` exist in the target repo (skill should fail-loud if any label is missing — list them and ask Anis to create or rename)
- `decision:anis` label is added wherever Anis input is needed

## Output to user

```
Repo:       chaibi-labs/<repo>
Created:    <count> issues
URLs:       [<list>]
Skipped:    <count>  (with reasons: missing labels, etc.)
Dry run:    yes | no
```
