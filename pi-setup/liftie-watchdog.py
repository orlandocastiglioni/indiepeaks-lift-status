#!/usr/bin/env python3
"""Hourly watchdog for the Liftie publish pipeline.

Alerts (via ntfy.sh, topic in NTFY_TOPIC env) when:
1. the last publish run recorded in status/_health.json is older than 2 hours
2. commits have piled up locally without reaching GitHub
3. the last liftie-publish run exited non-zero
4. during ski season (Nov 15 - Apr 15), any resort that once had data has
   been empty for 7+ consecutive days (parser-rot signal)

Check 1 alone is not enough: _health.json is written by the scrape, before the
push, so a push that fails leaves it looking perfectly fresh. That is exactly
what happened 2026-09-02 to 2026-09-08 -- the remote moved ahead, every push
was rejected as non-fast-forward, the feed froze for six days, and the watchdog
reported "all healthy" every morning. Checks 2 and 3 watch the delivery half of
the pipeline, which is the half that actually broke.
"""

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path.home() / "lift-status-data"
HEALTH = REPO / "status" / "_health.json"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
STALE_HOURS = 2
ROT_DAYS = 7
PUBLISH_UNIT = "liftie-publish.service"
STATE = Path.home() / ".liftie-watchdog-state.json"
REALERT_HOURS = 6


TS_FMT = "%Y-%m-%dT%H:%M:%SZ"


def parse_ts(ts):
    return datetime.strptime(ts, TS_FMT).replace(tzinfo=timezone.utc)


def in_season(now):
    m, d = now.month, now.day
    return (m == 11 and d >= 15) or m == 12 or m <= 3 or (m == 4 and d <= 15)


def unpushed_commits():
    """Commits on main that have not reached origin/main, or None if unknown.

    Uses the local origin/main ref without fetching: a successful push is what
    advances it, so a stalled push shows up here even with no network.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "rev-list", "--count", "origin/main..HEAD"],
            capture_output=True, text=True, timeout=60, check=True,
        )
        return int(out.stdout.strip())
    except (subprocess.SubprocessError, OSError, ValueError) as err:
        print(f"WARN: could not count unpushed commits: {err}")
        return None


def publish_unit_failed():
    """True when the last liftie-publish run exited non-zero."""
    try:
        out = subprocess.run(
            ["systemctl", "show", "-p", "Result", "--value", PUBLISH_UNIT],
            capture_output=True, text=True, timeout=60, check=True,
        )
        return out.stdout.strip() not in ("success", "")
    except (subprocess.SubprocessError, OSError) as err:
        print(f"WARN: could not read {PUBLISH_UNIT} result: {err}")
        return False


def alert(title, message, priority="high", tags="warning,ski"):
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode(),
        headers={"Title": title, "Priority": priority, "Tags": tags},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()
    print(f"ALERT sent: {title}: {message}")


def load_state():
    try:
        return json.loads(STATE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state):
    try:
        STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    except OSError as err:
        print(f"WARN: could not write {STATE}: {err}")


def notify(problems, now):
    """Send alerts, re-sending a still-broken thing only every REALERT_HOURS.

    This runs hourly, so alerting unconditionally would have meant 144 identical
    notifications during the six-day September outage -- which is how people
    learn to swipe these away. Each distinct problem pages at most every six
    hours, and says how long it has been going. When one clears, a single
    low-priority all-clear closes the loop so silence is never ambiguous.
    """
    state = load_state()
    active = {key: (title, message) for key, title, message in problems}

    for key, (title, message) in sorted(active.items()):
        since = state.get(key, {}).get("since")
        last = state.get(key, {}).get("lastAlerted")
        if since is None:
            state[key] = {"since": now.strftime(TS_FMT)}
        else:
            hours_broken = (now - parse_ts(since)).total_seconds() / 3600
            message += f" (ongoing for {hours_broken:.0f}h)"
        if last and (now - parse_ts(last)).total_seconds() / 3600 < REALERT_HOURS:
            print(f"suppressed (alerted <{REALERT_HOURS}h ago): {title}")
            continue
        alert(title, message)
        state[key]["lastAlerted"] = now.strftime(TS_FMT)

    for key in [k for k in state if k not in active]:
        if state[key].get("lastAlerted"):
            alert("Liftie pipeline recovered",
                  f"{key}: resolved. The pipeline looks healthy again.",
                  priority="low", tags="white_check_mark,ski")
        del state[key]

    save_state(state)


def main():
    now = datetime.now(timezone.utc)
    problems = []

    if not HEALTH.exists():
        problems.append(("health-missing",
                         "Liftie publish health file missing", str(HEALTH)))
    else:
        health = json.loads(HEALTH.read_text())
        age_h = (now - parse_ts(health["lastRun"])).total_seconds() / 3600
        if age_h > STALE_HOURS:
            problems.append((
                "scrape-stale",
                "Liftie scrape has stopped",
                f"Last publish run was {age_h:.1f}h ago (limit {STALE_HOURS}h). "
                "Check liftie.service / liftie-publish.timer on the pi.",
            ))
        behind = unpushed_commits()
        if behind:
            problems.append((
                "push-stalled",
                "Liftie publish is not reaching GitHub",
                f"{behind} commit(s) are stuck on the pi and have not been pushed. "
                "The scrape is running but the feed is frozen. Usually the remote "
                "moved ahead and push is rejected: run 'git pull --no-rebase' in "
                "~/lift-status-data, resolve any conflicts, and let the timer catch up.",
            ))

        if publish_unit_failed():
            problems.append((
                "publish-unit-failed",
                "Liftie publish service is failing",
                f"The last {PUBLISH_UNIT} run exited non-zero. "
                f"Check 'journalctl -u {PUBLISH_UNIT} -n 50' on the pi.",
            ))

        if in_season(now):
            rotten = []
            for rid, entry in sorted((health.get("resorts") or {}).items()):
                last = entry.get("lastNonEmpty")
                if not last or entry.get("lifts") or entry.get("trails"):
                    continue
                days = (now - parse_ts(last)).days
                if days >= ROT_DAYS:
                    rotten.append(f"{rid} (empty {days}d)")
            if rotten:
                problems.append((
                    "parser-rot",
                    "Liftie parsers may have rotted",
                    "In-season resorts empty for 7+ days: " + ", ".join(rotten),
                ))

    notify(problems, now)
    if not problems:
        print("watchdog: all healthy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
