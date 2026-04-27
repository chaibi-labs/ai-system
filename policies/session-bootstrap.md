# Session Bootstrap Policy

Codex and local model sessions are **stateless** — each invocation starts cold. Without a defined bootstrap sequence, every session redoes work the previous one already did, and Codex quota burns silently.

## The mandatory read order

Every agent session, regardless of role, begins by reading **in this exact order**:

1. The linked GitHub issue (full body)
2. The most recent `task_spec` attached to the issue (if any)
3. The last 5 comments on the issue
4. The current Kanban column the issue sits in
5. The agent's role definition (`agents/<role>.yaml`) and prompt (`prompts/<role>.md`)
6. `policies/universal.md` and the policy file relevant to the current action (cost / liveness / release / etc.)

Only after this bootstrap does the session emit its first action.

## Branching rules

- Issue has zero comments and no `task_spec` → agent is in **initial planning mode**; proceed to `coder.plan` (or the role's first action).
- Issue has a `task_spec` but the latest comment is `BLOCKED:` → agent **re-enters `coder.plan`** with the BLOCKED reason as input.
- Bootstrap reads cannot complete (issue not found, repo state mismatched, network failure) → agent **halts with STUCK** status; never proceeds on partial context.
- Bootstrap reads count toward heartbeat (`policies/liveness-policy.md` §22.5.5) — they are progress events.

## The principle

**State lives in the issue, not in the session.** The session is a thin compute layer that hydrates from the issue and writes back to it. This is what makes the system robust to:

- Stateless model calls
- Quota-induced restarts
- Concurrent agent activity
- Anis closing the chat / terminal
- Cross-day continuity

If you find yourself wanting to "remember" something across sessions, write it to the issue or to `memory/`. Do not rely on the session.

## Pre-bootstrap kill-switch / quota check

The bootstrap reads burn Codex quota. Before doing them:

1. Check `~/.ai-system/HALT` — if present, exit cleanly.
2. Check `~/.ai-system/quota_state.json` — if `exhausted`, exit; if `red` and not critical-path, return `BLOCKED("codex quota red")`.

These two checks happen **before** the bootstrap reads, so they don't burn quota themselves.
