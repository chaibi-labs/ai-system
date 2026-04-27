---
name: nightly
description: 'Run the nightly self-improvement workflow on demand. Default level v1 = report-only (writes reports/nightly/YYYY-MM-DD.md with anti-stall report at top). Levels v2-v4 unlock additional capabilities per agents/nightly.yaml. NOT for autonomous merging — never enabled.'
metadata:
  openclaw:
    emoji: "🌙"
    requires:
      anyBins: ["python3", "gh"]
---

# /nightly — Self-improvement run

Trigger: `/nightly` (no arguments). Optionally `/nightly --level <v1|v2|v3|v4>` to preview a higher level (still respects current `agents/nightly.yaml.current_level` for actual writes).

## Pre-action checks

1. HALT switch
2. Quota probe — nightly is conservative on Codex (`policies/nightly-policy.md` budget caps it at 1 Codex task per night by default, **disabled** unless `current_level >= v2` AND day is on `codex_allowed_days`)

## What you do

```bash
# GH_TOKEN/GITHUB_TOKEN are injected by systemd from ~/.ai-system/secrets/.env
# at OpenClaw daemon start (see ~/.config/systemd/user/openclaw-gateway.service.d/
# secrets.conf). Agents inherit them via the process tree — no agent reads the
# secrets file directly, honoring policies/security-policy.md.
cd /home/anis/src/ai-system
git pull --ff-only
python3 scripts/nightly.py
```

The skeleton script writes `reports/nightly/YYYY-MM-DD.md`. The body of that report needs to be filled by the nightly agent (local model). Required sections in this exact order (per `prompts/nightly.md`):

1. **anti_stall_report** (top — `policies/liveness-policy.md` §22.5.8): STUCK tasks, tasks at >50% wall-clock budget, decision gates >24h, Codex quota state + ETA, cascade halts active, heartbeat-killed runs in last 24h
2. What happened in the last 24h (commits, PRs merged, issues moved)
3. Blocked work (Waiting for Anis + STUCK)
4. Broken workflows / failing CI
5. Repeated agent mistakes (same BLOCKED reason 3+ times, same test failure pattern, same scope creep)
6. Suggested improvements
7. Cost risks
8. Decisions needed from Anis (aggregated from all open gates)
9. Proposed next-day priorities

## Level capabilities (read agents/nightly.yaml `current_level`)

| Level | Allowed in addition to v1                                                  |
|-------|----------------------------------------------------------------------------|
| v1    | Reports only (default)                                                     |
| v2    | Create GitHub issues for improvements (label `agent:nightly`)              |
| v3    | Open PRs in `ai-system` (CI eval gate enforced)                            |
| v4    | Open low-risk PRs in product repos: docs/tests/lint only                   |

## Forbidden at every level

Spending money / paid APIs without approval, publishing, deploying, **merging any PR**, deleting repos/branches, weakening branch protection, touching `policies/security-policy.md` or `policies/cost-policy.md` (proposing via PR is OK; merging isn't nightly's call).

## Output to user

```
Report:     reports/nightly/YYYY-MM-DD.md
Level:      v<N>
STUCK:      <count> tasks
24h decisions overdue: <count>
Quota:      <state> · ETA-exhausted: <timestamp or null>
Cascade halts: <count>
Issues created: <count> (v2+)
PRs opened: <count> (v3+)
```

The user should treat the morning rhythm as: read this report top-to-bottom before any other priorities. The anti_stall_report is intentionally above the activity log so a stalled system is louder than a working one.
