#!/usr/bin/env python3
"""Daily watchdog for the Liftie publish pipeline.

Alerts (via ntfy.sh, topic in NTFY_TOPIC env) when:
1. the last publish run recorded in status/_health.json is older than 2 hours
2. during ski season (Nov 15 - Apr 15), any resort that once had data has
   been empty for 7+ consecutive days (parser-rot signal)
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HEALTH = Path.home() / "lift-status-data" / "status" / "_health.json"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
STALE_HOURS = 2
ROT_DAYS = 7


def parse_ts(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def in_season(now):
    m, d = now.month, now.day
    return (m == 11 and d >= 15) or m == 12 or m <= 3 or (m == 4 and d <= 15)


def alert(title, message):
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode(),
        headers={"Title": title, "Priority": "high", "Tags": "warning,ski"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()
    print(f"ALERT sent: {title}: {message}")


def main():
    now = datetime.now(timezone.utc)
    problems = []

    if not HEALTH.exists():
        problems.append(("Liftie publish health file missing", str(HEALTH)))
    else:
        health = json.loads(HEALTH.read_text())
        age_h = (now - parse_ts(health["lastRun"])).total_seconds() / 3600
        if age_h > STALE_HOURS:
            problems.append((
                "Liftie publish is stale",
                f"Last publish run was {age_h:.1f}h ago (limit {STALE_HOURS}h). "
                "Check liftie.service / liftie-publish.timer on the pi.",
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
                    "Liftie parsers may have rotted",
                    "In-season resorts empty for 7+ days: " + ", ".join(rotten),
                ))

    for title, message in problems:
        alert(title, message)
    if not problems:
        print("watchdog: all healthy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
