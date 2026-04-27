# Liveness & Anti-Stall Policy

Autonomous agentic systems fail by **halting silently** more often than by failing loudly. This policy keeps the system either making visible progress or visibly stuck — never quietly stalled.

This is a working summary; the rationale lives in §22.5 of `README_personal_ai_dev_studio.md`.

## §22.5.1 Per-task budgets

Every issue / `task_spec` carries a budget (defaults in `policies/liveness-budgets.yaml`). Exceeding any budget escalates to Anis — it does **not** silently retry.

```
max_plan_attempts:       2
max_executor_attempts:   3
max_codex_calls_per_task: 8
max_wall_clock_hours:    4
heartbeat_interval_minutes: 10
```

A task can request a larger budget at planning time, but the request itself is a decision gate.

## §22.5.2 Plan↔execute ping-pong cap

```
coder.plan → coder.execute → BLOCKED → coder.plan  =  1 cycle
> 2 cycles for the same task  =  escalate to STUCK
```

Each cycle's plan and BLOCKED reason are **appended** to the issue, never overwritten.

## §22.5.3 Decision-gate SLA

```
Question to Anis emitted → task moves to "Waiting for Anis"
24h with no response → task is parked; agent moves to next eligible work
Daily morning report aggregates open decisions into one nudge
7 days unanswered → nightly proposes archive or safe default (Anis confirms)
```

`Waiting for Anis` is not allowed to become a graveyard.

## §22.5.4 Quota-aware degradation

Codex quota is the system's throughput ceiling. Explicit fallback modes:

```yaml
codex_quota_states:
  green:    # >50% remaining
    behavior: normal operation
  yellow:   # 20-50% remaining
    behavior: critical-path planning only; defer nightly Codex use
  red:      # <20% remaining
    behavior: planner-draft-only mode; no executor runs kicked off
  exhausted:
    behavior: report-only mode; no new tasks; surface to Anis as agent:liveness issue
```

State transitions are emitted as GitHub issues with the `agent:liveness` label, **not** silently logged.

**Measurement:** `scripts/codex_quota_probe.py` runs before every planner session and writes `~/.ai-system/quota_state.json`. The orchestrator reads that file with the same one-line discipline as the HALT check.

## §22.5.5 Heartbeat rule

Every active agent run emits a progress event at minimum once per `heartbeat_interval_minutes`. Progress events are one of:

- A commit
- A test run with captured output
- A `BLOCKED` status with a specific question
- A state transition on the task card
- A tool-call result that visibly advanced the spec

If the heartbeat window passes with no event, the run is **killed** and the task is marked `STUCK`. **"Thinking" without artifact is not progress.**

## §22.5.6 STUCK as a first-class Kanban state

`STUCK` is a column on the GitHub Project board, alongside Inbox / Spec Needed / Ready / In Progress / Review / Waiting for Anis / Done / Parked.

Tasks enter `STUCK` when any of these fire:

- Any budget in §22.5.1 is exceeded
- Ping-pong cap in §22.5.2 is hit
- Heartbeat in §22.5.5 is missed
- A cascade halt (§22.5.7) blocks them
- The executor returns BLOCKED for a reason the planner cannot resolve

`STUCK` tasks appear at the top of the morning report, before priorities. They are surfaced in real time via OpenClaw's `/liveness-status` skill — not waiting for the nightly cycle.

## §22.5.7 Cascade halt: "main is red"

If `main` CI fails on any active product repo:

- All `coder.execute` steps for that repo pause
- Only allowed work: a fix branch targeting the failing check
- Reviewer agent's first job becomes triaging the failing check
- Other products are unaffected

Prevents the common stall pattern where agents pile new branches on top of a broken `main`.

## §22.5.8 Anti-stall report

The nightly report's **top** section, mandatory:

```
anti_stall_report:
  - tasks currently STUCK (with reason, age, last event)
  - tasks at >50% of their wall-clock budget
  - decision gates older than 24h
  - Codex quota state and projected exhaustion time
  - cascade halts active
  - heartbeat-killed runs in the last 24h (with last event before kill)
```

Principle: **a stalled system must be louder than a working one**, because the working one is self-evident from commits and PRs while a stall produces nothing on its own.

## §22.5.9 Emergency stop (kill switch)

Global manual override:

```
File: ~/.ai-system/HALT
```

- Before every agent action — planner, executor, nightly, OpenClaw skill — the orchestrator checks for this file.
- If present → agent exits with status `HALTED`, writes one line to the active issue, and stops. No retries, no graceful drain.
- One-line check at the top of every agent script:
  `if Path("~/.ai-system/HALT").expanduser().exists(): sys.exit(0)`
- Happens **before** the bootstrap reads of `policies/session-bootstrap.md`, so it does not burn Codex quota.

Anis triggers it with:

```
touch ~/.ai-system/HALT     # stop everything
rm    ~/.ai-system/HALT     # resume
```
