# Skills

OpenClaw workspace skills for Anis's Personal AI Dev Studio.

These are versioned here in `ai-system/` and symlinked into the live OpenClaw workspace (`~/.openclaw/workspace/skills/<name>`) so OpenClaw picks them up. Edit here, commit, pull on the host, and re-link if a new skill is added.

## Skills

| Trigger              | Purpose                                                                   |
|----------------------|---------------------------------------------------------------------------|
| `/plan`              | Coder planner — emit a `task_spec` for an issue                           |
| `/review`            | Reviewer — review a PR against its `task_spec`                            |
| `/nightly`           | Nightly self-improvement run (level v1 = report only)                     |
| `/repo-health`       | Verify ai-system layout (`scripts/repo_health.py`)                        |
| `/create-issues`     | Batch-create issues from a YAML/JSON manifest                             |
| `/summarize-prs`     | Open-PR overview across all `chaibi-labs/*` repos                         |
| `/liveness-status`   | Real-time anti-stall view: STUCK, quota, decision gates, cascade halts    |

## Forbidden (not registered as skills, intentionally)

The plan §17 explicitly lists these as **never enable initially**:

- `/auto-merge`
- `/publish`
- `/buy`
- `/deploy-production`
- `/delete`

Any future enable is a deliberate Anis call, with a release-style checklist (`policies/release-policy.md`).

## Source-of-truth flow

1. Edit a `SKILL.md` here.
2. Commit + PR to `chaibi-labs/ai-system` (the meta-system follows its own rules).
3. After merge, on the host: `cd ~/src/ai-system && git pull`.
4. The symlink at `~/.openclaw/workspace/skills/<name>` points to `~/src/ai-system/skills/<name>` — no copy needed.
5. OpenClaw picks up changes automatically (or `openclaw skills list` to verify).

## How a skill body works

The frontmatter (`name`, `description`, `metadata.openclaw.*`) is read by OpenClaw. The markdown body is the prompt the LLM uses when the user invokes the skill — it tells the model what bash commands to run, what to read, and what output format to produce.

All skills here pre-flight with the same discipline:

- Check `~/.ai-system/HALT` (kill switch — `policies/liveness-policy.md` §22.5.9)
- Check `~/.ai-system/quota_state.json` (quota-aware degradation — §22.5.4)
- Source `~/.ai-system/secrets/.env` for `GH_TOKEN`
- `cd ~/src/ai-system && git pull --ff-only` so the skill always runs against current `main`
