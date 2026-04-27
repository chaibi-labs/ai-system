---
name: liveness-status
description: 'Surface the studio''s liveness state on demand — STUCK queue, Codex quota state, open decision gates, cascade halts, heartbeat-killed runs. Read-only. The principle: a stalled system must be louder than a working one. Use any time it feels like nothing is happening.'
metadata:
  openclaw:
    emoji: "🚦"
    requires:
      anyBins: ["python3", "gh"]
---

# /liveness-status — Real-time anti-stall view

Trigger: `/liveness-status`

This is the on-demand counterpart to the nightly anti_stall_report (`policies/liveness-policy.md` §22.5.8). Use it whenever you want a "where is the system right now?" answer without waiting for the nightly cycle.

## What you do

```bash
[[ -f /home/anis/.ai-system/HALT ]] && { echo "🛑 HALTED — kill switch is active. Remove ~/.ai-system/HALT to resume."; exit 0; }
# GH_TOKEN/GITHUB_TOKEN are injected by systemd from ~/.ai-system/secrets/.env
# at OpenClaw daemon start (see ~/.config/systemd/user/openclaw-gateway.service.d/
# secrets.conf). Agents inherit them via the process tree — no agent reads the
# secrets file directly, honoring policies/security-policy.md.
cd /home/anis/src/ai-system
python3 scripts/codex_quota_probe.py --quiet
```

Then collect:

### 1. Codex quota state

```bash
cat ~/.ai-system/quota_state.json
```

Pull `state`, `remaining_pct`, `sessions_used_in_window`, `estimated_exhaustion_at`.

### 2. STUCK queue

Tasks in the GitHub Project #1 with Status = STUCK:

```bash
gh project item-list 1 --owner chaibi-labs --format json
# filter to items where Status == "STUCK"
```

For each, also fetch the issue to surface: reason for STUCK, age, last event.

### 3. Decision gates older than 24h

Issues with `decision:anis` label that have been in `Waiting for Anis` for >24h (per `policies/liveness-policy.md` §22.5.3 SLA):

```bash
gh issue list --search "label:decision:anis" --json number,title,updatedAt,labels --limit 50
```

Filter client-side for `updatedAt > 24h ago`.

### 4. Cascade halts active

For each active product repo, check `main` CI status:

```bash
gh repo list chaibi-labs --json name --limit 100
# for each: gh run list --repo <name> --branch main --status failure --limit 1
```

If `main` is red on any active product, raise a cascade-halt flag.

### 5. Heartbeat-killed runs in last 24h

(Not yet implemented — hook in the nightly will append these to a log; surface here when the log exists. For now, output `not yet tracked`.)

## Output format

```
🚦 Liveness — <timestamp>

Kill switch:        🛑 HALTED  /  ✓ off
Codex quota:        🟢 green | 🟡 yellow | 🔴 red | ⛔ exhausted  ·  <pct>% remaining
                    Used <N> / <CAP> sessions in current 5h window
                    ETA-exhausted: <timestamp or null>

STUCK tasks:        <count>
  - chaibi-labs/<repo>#<N>  ·  age <D>d  ·  reason: <budget-exceeded|ping-pong|heartbeat-miss|cascade>
  - ...

Open decision gates (>24h):  <count>
  - chaibi-labs/<repo>#<N>  ·  age <D>d  ·  <title>
  - ...

Cascade halts:      <count>
  - chaibi-labs/<repo> · main is red · only fix-branch work allowed (§22.5.7)
  - ...

Heartbeat-killed (24h):  not yet tracked
```

## When to act

- 🔴 / ⛔ quota → defer non-critical work, switch nightly to local-only
- STUCK > 0 → unblock manually or tag with `decision:anis` if Anis input needed
- Decision gates > 24h → answer them in the morning rhythm; the longer they sit, the more downstream work piles up
- Cascade halt → fix `main` first, all other coder work pauses until green
