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
    "49-degrees-north", "abondance", "amihari-onsen", "antelope-butte", "aomori-spring",
    "apex-mountain-resort", "arctic-valley", "avoriaz", "axamer-lizum", "baldy-mountain-resort",
    "baqueira-beret", "bear-creek-pa", "bear-valley", "bear-valley-adventure-company",
    "beaver-mountain", "berkshire-east", "bethel-village-trails", "big-moose", "big-powderhorn",
    "big-rock", "big-white", "bjorkliden", "black-jack", "black-mountain-me",
    "black-mountain-nh", "blue-knob", "bolton-valley", "bousquet", "brundage", "bryce-resort",
    "buffalo-ski-center", "burke-mountain", "calabogie", "caledonia-nordic", "camden-snow-bowl",
    "canaan-valley", "canmore-ski-village", "cannon", "castle-mountain", "cataloochee",
    "catamount-ny", "catamount-outdoor", "centre-vorlage", "champery", "chatel", "cherry-peak",
    "chestnut-mountain", "chinapeak", "christie-mountain", "cooper-spur", "corralco",
    "crosscut-mountain-sports-center", "crystal-mountain-mi", "cupid-valley", "dodge-ridge",
    "dog-creek-lodge-nordic-center", "donner-ski-ranch", "dynaland", "eagle-point",
    "eaglecrest", "echo-mountain", "elferbahnen", "erciyes", "fellhorn-kanzelwand",
    "fort-kent-outdoor-center", "franconia-village-xc", "geto-kogen", "glencoe", "glenshee",
    "glungezer", "granby-ranch", "great-bear", "great-glen-trails", "greek-peak",
    "hachimantai-shimokura", "hatley-pointe", "haymaker-nordic-center", "heuberg",
    "high-point-xc", "hirugano-kogen", "hochoetz", "hochzeiger", "hockley-valley", "hodaigi",
    "hohsaas", "homestake-lodge", "hoodoo", "howelsen-hill", "hudson-bay-mountain",
    "huff-hills", "hunt-hollow", "hyland-hills", "ifen", "jackson-xc", "jay-peak",
    "kamui-ski-links", "kaunertaler-gletscher", "kimberley-nordic", "king-pine", "krvavec",
    "kuehtai", "la-chapelle-dabondance", "leavenworth-ski-hill", "les-7-laux", "les-gets",
    "leukerbad-torrent", "levi", "loch-lomond", "lost-trail-powder-mountain", "lost-valley",
    "loup-loup", "loveland", "magic-mountain", "maiko-snow-resort", "mala-upa", "manning-park",
    "manning-park-xc", "maple-ski-ridge", "marble-mountain", "marquette-mountain",
    "massanutten", "massif-du-sud", "mcintyre", "minocqua-winter-park", "mohawk-mountain",
    "mont-edouard", "mont-rigaud", "mont-ripley", "mont-sutton", "montage-mountain",
    "montana-snowbowl", "morgins", "mount-kato", "mount-racey", "mt-abram", "mt-holiday",
    "mt-la-crosse", "mt-shasta", "mt-washington-bc", "mthigh", "mthood", "muica-snow-resort",
    "murray-ridge", "muttereralm", "nayoro-piyashiri", "nebelhorn", "nelson-nordic",
    "nickel-plate-nordic", "ninox-snow-park", "nordkette", "norefjell", "nubs-nob",
    "ober-mountain", "okunakayama", "owlshead", "palandoken", "palcall-tsumagoi", "pats-peak",
    "patscherkofel", "pds-morzine", "pebble-creek", "peek-n-peak", "pila",
    "pitztaler-gletscher", "plain-valley-ski-trails", "pomerelle", "powder-ridge-mn",
    "powderhorn", "quarry-road-trails", "ragged-mountain", "rangeley-lakes-trail-center",
    "rangger-koepfl", "rauriser-hochalmbahnen", "red-lodge-mountain", "rikert", "riksgransen",
    "saddleback", "saint-jean-daulps", "saskadena-six", "sasquatch-mountain", "schlick-2000",
    "schuss-mountain", "serlesbahnen", "shames-mountain", "shawnee-mountain", "silver-mountain",
    "ski-big-bear", "ski-sawmill", "skiwelt", "smokey-mountain", "smuggs", "snow-king",
    "snow-ridge", "snowstar", "soellereck", "sovereign-lake", "spirit-mountain",
    "steamboat-ski-touring-center", "steinplatte", "stoten", "strandafjellet", "stubai-glacier",
    "sunburst", "sundown-mountain", "sunlight-mountain-resort", "swain", "takasu-snow-park",
    "tamarack-resort", "tazawako", "telemark-nordic", "tenney-mountain", "terry-peak",
    "the-loppet", "togakushi", "torgon", "trapp-family-lodge", "treetops", "trollhaugen",
    "turpin-meadow-ranch", "tussey-mountain", "val-direne", "vallee-bleue", "walmendingerhorn",
    "washigatake", "waterville", "west-mountain", "whaleback-mountain", "white-pine-touring",
    "whitehorse-nordic", "whitepia-takasu", "williams-lake-xc", "wintergreen", "winterplace",
    "wisp", "woodstock-nordic-center", "yuzawa-nakazato",
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


def reason(stderr):
    """The line of git's push output that says why, not 'To <url>'."""
    for line in stderr.splitlines():
        if "rejected" in line or line.startswith("error:"):
            return line.strip()
    return stderr.splitlines()[0] if stderr else "no detail"


def push(attempts=3):
    """Push to origin/main, recovering from a remote that moved ahead.

    A plain push is not enough: anything landing on main from elsewhere -- a
    merged PR, a session on the laptop -- makes every subsequent push here a
    non-fast-forward rejection, and this runs unattended every fifteen minutes.
    Between 2026-09-02 and 2026-09-08 that froze the public feed for six days
    while the scrape carried on committing locally.

    On rejection, rebase the local status commits onto origin/main and retry.
    They are generated data with no other consumer, so replaying them on top is
    safe and keeps history linear. A rebase that conflicts is NOT resolved here:
    a conflict means the remote deliberately changed or deleted the same status
    files (as the 26/27 roster prune did), and picking a side automatically
    would silently revert someone's intent. Abort, fail, let the watchdog page.
    """
    for attempt in range(1, attempts + 1):
        try:
            git("push", "origin", "main")
            return True
        except subprocess.CalledProcessError as err:
            stderr = (err.stderr or "").strip()
            if attempt == attempts:
                log(f"ERROR: git push failed after {attempts} attempts: {stderr}")
                return False
            log(f"Push rejected (attempt {attempt}/{attempts}); "
                f"rebasing onto origin/main and retrying. Remote said: "
                f"{reason(stderr)}")
            try:
                git("fetch", "origin", "main")
                git("rebase", "origin/main")
            except subprocess.CalledProcessError as rebase_err:
                git("rebase", "--abort", check=False)
                log("ERROR: could not rebase onto origin/main, so the local "
                    "commits stay unpushed and the feed is stalled. This "
                    "usually means the remote changed or deleted the same "
                    "status files. Resolve by hand in "
                    f"{REPO}. Git said: {(rebase_err.stderr or '').strip()}")
                return False
    return False


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


def write_index(names):
    """status/_index.json: id -> display name for every published resort,
    so the app can discover new resorts without shipping its own list."""
    index_file = STATUS_DIR / "_index.json"
    index = {"resorts": {rid: {"name": name} for rid, name in sorted(names.items())}}
    previous = None
    if index_file.exists():
        try:
            previous = json.loads(index_file.read_text())
        except json.JSONDecodeError:
            pass
    if index != previous:
        index_file.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
        return True
    return False


def main():
    STATUS_DIR.mkdir(exist_ok=True)
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    changed = []
    results = {}
    errors = []
    names = {}

    for resort_id in sorted(RESORTS):
        data = fetch(resort_id)
        if data is None:
            errors.append(resort_id)
            continue
        results[resort_id] = counts(data)
        if data.get("name"):
            names[resort_id] = data["name"]

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

    # if EVERY resort failed to fetch, liftie is down (e.g. still starting
    # after a reboot) - bail before rewriting _health/_index, which would
    # otherwise clobber them with an all-empty snapshot.
    if not results and errors:
        log(f"All {len(errors)} resorts failed to fetch; liftie is likely down. "
            "Skipping publish to preserve _health/_index.")
        return 0

    if write_health(fetched_at, results, errors):
        changed.append("_health")
    if write_index(names):
        changed.append("_index")

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
    if not push():
        return 1
    log(f"Published {len(changed)} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
