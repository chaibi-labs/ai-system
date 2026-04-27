#!/usr/bin/env bash
# init_host.sh — initializes ~/.ai-system/ on the host (idempotent).
#
# Sets up:
#   ~/.ai-system/                   (chmod 700)
#   ~/.ai-system/secrets/           (chmod 700)
#   ~/.ai-system/secrets/.env       (chmod 600, empty if missing)
#   ~/.ai-system/codex_sessions.log (chmod 600)
#   ~/.ai-system/quota_state.json   (initial state: green)
#
# Does NOT create ~/.ai-system/HALT (that's a tripwire — present means STOP).
#
# Run on every host (Mac for orchestration, WSL Ubuntu for execution).

set -euo pipefail

ROOT="$HOME/.ai-system"
mkdir -p "$ROOT"
chmod 700 "$ROOT"

mkdir -p "$ROOT/secrets"
chmod 700 "$ROOT/secrets"

if [[ ! -f "$ROOT/secrets/.env" ]]; then
  cat > "$ROOT/secrets/.env" <<'EOF'
# ~/.ai-system/secrets/.env
# Personal AI Dev Studio secrets. Never committed. chmod 600.
#
# Loaded by systemd at OpenClaw daemon start via the drop-in at
# ~/.config/systemd/user/openclaw-gateway.service.d/secrets.conf.
# Agents NEVER read this file directly — they inherit env vars from
# the daemon's process tree (see policies/security-policy.md).
#
# Required at MVP — and only these:
GITHUB_TOKEN=
GH_TOKEN=
GITHUB_USERNAME=DasGewuerz

# Codex authenticates via ChatGPT login (subscription), not API key.
# The presence of OPENAI_API_KEY here is a configuration error per
# policies/cost-policy.md — leave it absent.
EOF
  chmod 600 "$ROOT/secrets/.env"
  echo "Created $ROOT/secrets/.env (fill in GITHUB_TOKEN; mirror to GH_TOKEN)"
fi

if [[ ! -f "$ROOT/codex_sessions.log" ]]; then
  : > "$ROOT/codex_sessions.log"
  chmod 600 "$ROOT/codex_sessions.log"
fi

if [[ ! -f "$ROOT/quota_state.json" ]]; then
  cat > "$ROOT/quota_state.json" <<'EOF'
{
  "state": "green",
  "remaining_pct": 100.0,
  "sessions_used_in_window": 0,
  "note": "initial seed; codex_quota_probe.py will refresh on next run"
}
EOF
  chmod 600 "$ROOT/quota_state.json"
fi

echo "Host initialized:"
ls -la "$ROOT"
echo ""
echo "Next steps:"
echo "  1. Edit $ROOT/secrets/.env and fill in GITHUB_TOKEN"
echo "  2. Run scripts/codex_quota_probe.py to refresh quota state"
echo "  3. The HALT tripwire is NOT created here — touch ~/.ai-system/HALT to pause everything"
