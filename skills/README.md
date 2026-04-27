# Skills

OpenClaw workspace skills for Anis's Personal AI Dev Studio.

These are versioned here in `ai-system/` and registered with OpenClaw via `skills.load.extraDirs` in `~/.openclaw/openclaw.json`. The host points at `~/src/ai-system/skills/` directly — no copy, no symlink. Edit here, commit, `git pull` on the host, and OpenClaw's filesystem watcher picks up the change automatically (debounced via `skills.load.watchDebounceMs`).

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
4. OpenClaw's `skills.load.extraDirs` already includes `/home/anis/src/ai-system/skills`, so the new content is picked up by the filesystem watcher.
5. Verify with `openclaw skills list` — your skill should appear with source `openclaw-extra`.

## One-time host setup (already done)

```bash
openclaw config set skills.load.extraDirs '["/home/anis/src/ai-system/skills"]'
```

## How a skill body works

The frontmatter (`name`, `description`, `metadata.openclaw.*`) is read by OpenClaw. The markdown body is the prompt the LLM uses when the user invokes the skill — it tells the model what bash commands to run, what to read, and what output format to produce.

All skills here pre-flight with the same discipline:

- Check `~/.ai-system/HALT` (kill switch — `policies/liveness-policy.md` §22.5.9)
- Check `~/.ai-system/quota_state.json` (quota-aware degradation — §22.5.4)
- Source `~/.ai-system/secrets/.env` for `GH_TOKEN`
- `cd ~/src/ai-system && git pull --ff-only` so the skill always runs against current `main`
