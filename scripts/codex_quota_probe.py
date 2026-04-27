#!/usr/bin/env python3
"""
codex_quota_probe.py — measurement leg of liveness §22.5.4.

Runs before every planner session. Estimates remaining Codex quota from a
rolling 5-hour window of session timestamps logged to
~/.ai-system/codex_sessions.log, and writes the resulting state to
~/.ai-system/quota_state.json.

The orchestrator reads quota_state.json with the same one-line discipline
as the HALT check:

    state = json.loads(Path("~/.ai-system/quota_state.json").expanduser().read_text())
    if state["state"] == "exhausted":
        sys.exit(0)
    if state["state"] == "red" and not task.is_critical_path:
        return BLOCKED("codex quota red")

Stdlib only.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Configuration --------------------------------------------------------------

# 5-hour rolling window matches ChatGPT subscription rate-limit semantics.
WINDOW_SECONDS = 5 * 60 * 60

# Heuristic: assume the subscription tolerates ~50 Codex sessions per window
# before throttling. Tune by observing real behavior — if you hit limits at
# 30 sessions, lower this. The exact value is a moving target.
SESSIONS_PER_WINDOW = 50

# State thresholds (% remaining)
THRESHOLD_GREEN = 50
THRESHOLD_YELLOW = 20
THRESHOLD_RED = 5
# < THRESHOLD_RED → red; <= 0 → exhausted

AI_SYSTEM_DIR = Path("~/.ai-system").expanduser()
SESSIONS_LOG = AI_SYSTEM_DIR / "codex_sessions.log"
QUOTA_STATE = AI_SYSTEM_DIR / "quota_state.json"


def ensure_dir() -> None:
    AI_SYSTEM_DIR.mkdir(parents=True, exist_ok=True)


def read_recent_session_count() -> int:
    if not SESSIONS_LOG.exists():
        return 0

    cutoff = time.time() - WINDOW_SECONDS
    count = 0
    with SESSIONS_LOG.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ts_str = line.split("\t", 1)[0]
                ts = datetime.fromisoformat(ts_str).timestamp()
            except (ValueError, IndexError):
                continue
            if ts >= cutoff:
                count += 1
    return count


def classify(remaining_pct: float) -> str:
    if remaining_pct <= 0:
        return "exhausted"
    if remaining_pct < THRESHOLD_RED:
        return "red"
    if remaining_pct < THRESHOLD_YELLOW:
        return "yellow"
    return "green"


def estimated_exhaustion_eta(used: int, window_seconds: int) -> str | None:
    """Naive ETA: if the burn rate stays linear, when do we hit 0?"""
    if used == 0 or used >= SESSIONS_PER_WINDOW:
        return None
    seconds_per_session = window_seconds / max(used, 1)
    seconds_until_exhausted = (SESSIONS_PER_WINDOW - used) * seconds_per_session
    eta = datetime.now(timezone.utc).timestamp() + seconds_until_exhausted
    return datetime.fromtimestamp(eta, tz=timezone.utc).isoformat()


def main() -> int:
    ensure_dir()
    used = read_recent_session_count()
    remaining_pct = max(0.0, 100.0 * (1.0 - used / SESSIONS_PER_WINDOW))
    state = classify(remaining_pct)

    payload = {
        "state": state,
        "remaining_pct": round(remaining_pct, 1),
        "sessions_used_in_window": used,
        "sessions_per_window": SESSIONS_PER_WINDOW,
        "window_seconds": WINDOW_SECONDS,
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "estimated_exhaustion_at": estimated_exhaustion_eta(used, WINDOW_SECONDS),
        "note": (
            "Heuristic estimate from rolling window of session timestamps. "
            "When the Codex CLI exposes a usage endpoint, prefer it as the "
            "source of truth and treat this as fallback."
        ),
    }
    QUOTA_STATE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if "--quiet" not in sys.argv:
        print(json.dumps(payload, indent=2))

    # Exit codes the orchestrator can branch on without reading the file:
    return {"green": 0, "yellow": 0, "red": 2, "exhausted": 3}[state]


if __name__ == "__main__":
    sys.exit(main())
