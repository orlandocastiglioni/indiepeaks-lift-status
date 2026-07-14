#!/usr/bin/env python3
"""Publish lift status from the local Liftie instance to the
indiepeaks-lift-status GitHub repo.

For each resort: GET the local Liftie API, validate the payload, and write
status/<id>.json only when the "lifts" payload actually changed. One commit
per run covering all changed resorts; no commit when nothing changed.
Logs go to stdout/stderr (journald via the liftie-publish systemd unit).
"""

import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LIFTIE = "http://127.0.0.1:3001/api/resort/{}"
REPO = Path.home() / "lift-status-data"
STATUS_DIR = REPO / "status"

RESORTS = [
    "49-degrees-north", "berkshire-east", "big-moose", "big-white",
    "bolton-valley", "burke-mountain", "caberfae-peaks", "calabogie",
    "canaan-valley", "cannon", "castle-mountain", "cataloochee", "chinapeak",
    "cooper-spur", "donner-ski-ranch", "dynaland",
    "eagle-point", "echo-mountain", "glencoe", "granite-peak", "greek-peak",
    "hirugano-kogen", "hochzeiger", "hoodoo", "jay-peak", "king-pine",
    "little-switzerland", "loveland", "lutsen-mountains", "manning-park",
    "mission-ridge", "mt-abram", "mt-la-crosse", "mthigh", "mthood",
    "nayoro-piyashiri", "nordic-mountain", "okunakayama", "owlshead",
    "palcall-tsumagoi", "pats-peak", "pitztaler-gletscher",     "ragged-mountain", "red-lodge-mountain", "saddleback", "saskadena-six",
    "sasquatch-mountain", "shawnee-mountain", "ski-sawmill", "skiwelt",
    "snow-ridge", "snowriver", "sundown-mountain", "swain",
    "takasu-snow-park", "togakushi", "washigatake", "waterville",
    "west-mountain", "wintergreen", "winterplace", "wisp",
]


def log(msg):
    print(msg, flush=True)


def fetch(resort_id):
    """Return the parsed API response, or None (logged) on any problem."""
    url = LIFTIE.format(resort_id)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            body = resp.read()
    except (urllib.error.URLError, OSError) as err:
        log(f"SKIP {resort_id}: request failed: {err}")
        return None
    try:
        data = json.loads(body)
    except json.JSONDecodeError as err:
        log(f"SKIP {resort_id}: response is not JSON: {err}")
        return None
    if not isinstance(data, dict) or ("lifts" not in data and "trails" not in data):
        log(f"SKIP {resort_id}: response has neither 'lifts' nor 'trails' key")
        return None
    return data


def git(*args, check=True):
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        check=check, capture_output=True, text=True,
    )


def counts(data):
    lifts = len((data.get("lifts") or {}).get("status") or {})
    trails_list = (data.get("trails") or {}).get("list")
    trails = len(trails_list) if trails_list else 0
    return lifts, trails


def write_health(fetched_at, results, errors):
    """status/_health.json: run stamp, per-resort item counts, error list, and
    resorts that had data at some point but are empty now (parser-rot signal).
    lastRun changes every run but only material changes trigger a commit."""
    health_file = STATUS_DIR / "_health.json"
    previous = {}
    if health_file.exists():
        try:
            previous = json.loads(health_file.read_text())
        except json.JSONDecodeError:
            pass
    prev_resorts = previous.get("resorts") or {}

    resorts = {}
    went_empty = []
    for resort_id, (lifts, trails) in sorted(results.items()):
        entry = {"lifts": lifts, "trails": trails}
        last_non_empty = (prev_resorts.get(resort_id) or {}).get("lastNonEmpty")
        if lifts or trails:
            entry["lastNonEmpty"] = fetched_at
        elif last_non_empty:
            entry["lastNonEmpty"] = last_non_empty
            went_empty.append(resort_id)
        resorts[resort_id] = entry

    health = {
        "lastRun": fetched_at,
        "resorts": resorts,
        "errors": sorted(errors),
        "emptyButPreviouslyPopulated": went_empty,
    }
    health_file.write_text(json.dumps(health, indent=2, sort_keys=True) + "\n")

    def material(doc):
        return {
            "resorts": {
                rid: {k: v for k, v in (entry or {}).items() if k != "lastNonEmpty"}
                for rid, entry in (doc.get("resorts") or {}).items()
            },
            "errors": doc.get("errors"),
            "emptyButPreviouslyPopulated": doc.get("emptyButPreviouslyPopulated"),
        }

    return material(health) != material(previous)


def main():
    STATUS_DIR.mkdir(exist_ok=True)
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    changed = []
    results = {}
    errors = []

    for resort_id in sorted(RESORTS):
        data = fetch(resort_id)
        if data is None:
            errors.append(resort_id)
            continue
        results[resort_id] = counts(data)

        out_file = STATUS_DIR / f"{resort_id}.json"
        if out_file.exists():
            try:
                previous = json.loads(out_file.read_text())
            except json.JSONDecodeError:
                previous = {}
            if previous.get("lifts") == data.get("lifts") and previous.get("trails") == data.get("trails"):
                continue  # unchanged - leave file and fetchedAt alone

        data["fetchedAt"] = fetched_at
        out_file.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        changed.append(resort_id)

    if write_health(fetched_at, results, errors):
        changed.append("_health")

    if not changed:
        log("No lift status changes; nothing to publish.")
        return 0

    log(f"Changed: {', '.join(changed)}")
    git("add", "status")
    # `git diff --cached --quiet` exits 1 when there is something to commit
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        log("Files identical after serialization; nothing to commit.")
        return 0
    git("commit", "-m", f"lift status update {fetched_at}")
    try:
        git("push", "origin", "main")
    except subprocess.CalledProcessError as err:
        log(f"ERROR: git push failed: {err.stderr.strip()}")
        return 1
    log(f"Published {len(changed)} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
