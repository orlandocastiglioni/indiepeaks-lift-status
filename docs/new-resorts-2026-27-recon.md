# Status recon — the resorts Indy added for 2026-27

**Date: 2026-09-02, extended 2026-09-03 and 2026-09-04.** Written while adding the 26/27 partners to the IndiePeaks
app, so the in-season parser session is a short job rather than a fresh survey.

Indy announced six new partners for 26/27: Frost Fire Park (ND), Kandatsu Snow
Resort (Japan), Pyhä Ski Resort (Finland), Scotts Cobble Nordic Center (NY),
Skeetawk (AK) and Ski Land (AK).

**None of them got a Liftie parser, and that is the finding, not a shortfall.**
Every source was fetched and read by hand on 2026-09-02. Four of the six publish
no per-lift or per-trail status at all — not "not in summer", but nowhere on the
site — and the remaining two cannot be parsed off-season without guessing.
`web.archive.org` is unreachable from the machine this recon ran on, so the
winter-fixture technique that built the 2026-07-12 batch was not available
either.

What shipped in the app instead: **report-link-only** `status-sources.json`
entries for the three that have a conditions page (`pyha-ski-resort`,
`scotts-cobble-nordic-center`, `skeetawk`), and **no entry** for the other
three, which falls back to the resort's `websiteURL`. Both tiers open in
SafariView, so a bot-walled site still works for the user.

## Per resort

| Resort | Conditions page | What it actually publishes | In-season action |
|---|---|---|---|
| **Skeetawk** (AK) | `skeetawk.com/snow-report` — 200, real page | Temperature, wind, new snow, snow depth, season total, avalanche-mitigation flag, a road-closure line and a message of the day. **No lift or trail rows**: the only `conditions__trails--icon` block in the DOM is inside an HTML comment, and the two lifts are not listed anywhere. | Recheck once, briefly. If it stays lift-less this is permanently report-link-only. |
| **Scotts Cobble Nordic Center** (NY) | `scottscobblenordic.com/trail-map-conditions` — 200 | A Google Sites page whose conditions are a hand-written prose update ("Scotts Cobble will be closed Saturday 3/21…"). Nothing enumerable. Same shape as the `jackson-xc` daily-report case. | Report-link-only. Do not try to parse prose into counts. |
| **Pyhä Ski Resort** (FI) | `pyha.fi/en/skiresort/slopes` — 200, titled "Pyhä slopes and lifts" | Summer content today; the URL is season-stable (it is *not* the Baqueira trap, whose path changes with the season). Nine named lifts appear as page content, with no status markers out of season. | **Best candidate of the six.** Check in December for (a) an XHR/JSON slope-status endpoint first — a real API beats scraping — and (b) the winter DOM of this same URL. |
| **Kandatsu Snow Resort** (JP) | none linked by Indy | `kandatsu.com` returns a hard **HTTP 403** to every scripted client, browser User-Agent and full headers included. Apache-level `403 Forbidden`, not a Cloudflare JS challenge, so this may be an IP/ASN block rather than a UA one. | Second candidate. Japanese resorts usually publish a ゲレンデ情報 slope table in winter. Try from the Pi's residential connection first — if it answers there, this is an ordinary parser job; if not, it needs the flaresolverr/renderd tier. |
| **Frost Fire Park** (ND) | none linked by Indy | `frostfirepark.org/trail-map-and-ski-days` is opening hours and ski-day dates, not conditions. `Scripts/find-report-pages.py` scored the whole site "none". | Recheck in season; likely nothing to parse. |
| **Ski Land** (AK) | none, by the resort's own account | `skilandfairbanks.com/skiing/` says it in as many words: "Follow our daily updates on Facebook to see our current lift weather status." There is no on-site status page. | Report-link-only at best; there is no scrapeable source unless they add one. |

No public JSON status API exists for any of the six —
`Scripts/find-status-apis.py` (homepages → conditions pages → same-domain and
vendor JS/iframes → wp-json routes, every candidate fetched and checked) came
back **0 verified, 0 leads, 1 blocked (Kandatsu), 6 total**.

## Second announcement — 2026-09-03

Indy announced six more the next day: Kendall Mountain (CO), King Pine (NH,
promoted from Allied to a full partner), Mont Kanasuta (QC), Ruka (FI), Togari
Onsen (JP) and Eastman Cross Country (NH). **Two of these are much better
parser candidates than anything in the first batch**, because their conditions
pages are aggregators this pipeline already parses:

| Resort | Conditions host | Already parsed here for | In-season action |
|---|---|---|---|
| **Mont Kanasuta** (QC) | `maneige.ski/stations/centre-plein-air-mont-kanasuta/` | `mont-habitant`, `vallee-bleue` (patch 0129, `"via": "flaresolverr"`) | Should be a descriptor + a reuse of the existing maneige parser. The host 403s every scripted client, browser UA included — expected, it is why those two already go through flaresolverr. |
| **Eastman Cross Country** (NH) | `nordic-pulse.com/ski-areas/US/NH/Eastman-Cross-Country` | `rikert`, `manning-park-xc` and 9 more (patches 0127 shared module + 0128) | Should be a one-line addition to the Nordic Pulse resort list. Trails-only (`"no": {"lifts": true}`), like the rest of them. |

Neither was written here: this session has no Node ≥ 23.8 (Liftie needs
URLPattern; the box has 22.22), so a parser could be typed but not run against
the suite, and an unverified parser is what the 2026-07 review exists to warn
about. Both are small, well-precedented jobs on the Pi.

The other three new ones look like the first batch: Kendall Mountain publishes
opening hours (`skikendall.com/hours-events`), Ruka a season-stable slopes page
that is summer content today (`ruka.fi/en/skiresort/slopes`), Togari a course
map (`togari.jp/winter/en/course_map/`). **King Pine needs nothing** — it is
already published here and read by the app; only its Indy pass tier changed.

## Third announcement — 2026-09-04

Five more announced; four new resorts (Showdown MT, Powder Ridge CT,
Heiligenblut-Großglockner AT, Engstligenalp CH) plus Jay Peak gaining
cross-country. All four new ones are report-link-only in the app —
`showdownmontana.com/grooming-report-trail-status`,
`powderridgepark.com/trail-report/` (403s scripted clients, SafariView-exempt),
`heiligenblut.at`'s ski-area page and `engstligenalp.ch/winter/betriebsinfo/`.
None points at an aggregator this pipeline already parses, so unlike Mont
Kanasuta and Eastman there is no cheap parser here; recheck in season.

**Two things in this repo want a look:**

- **`status/powder-ridge-mn.json` carries the wrong resort name.** Its payload
  reads `"name": "Powder Ridge Mountain Park & Resort"`, which is the
  **Connecticut** resort (`powderridgepark.com`, Middlefield CT) that joined the
  pass this season. This file is the **Minnesota** one — its own `href` is
  `powderridge.com/ski-ride/trail-map/`, which is correct — and Indy calls it
  simply "Powder Ridge". Nothing is mis-scraped, but the name is now actively
  confusing, because **there are two Powder Ridges on the pass**. Treat this as
  a second `crystal-mountain` MI/WA pair: they are 1,800 km apart with different
  hosts, so the app-side generator keeps them separate on the host match, but do
  not add a CT parser under a name that collides.
- **`jay-peak` publishes lifts only.** Jay Peak is now an alpine **+
  cross-country** partner (Indy flipped `data-isalpinexc` on its existing card
  rather than creating a "Jay Peak XC" resort). If Jay's site exposes nordic
  trail status, adding it would be the difference between the app showing half
  that resort's conditions and all of them.

## Fourth announcement — 2026-09-05

Five announced, four new resorts (Mt. Pisgah NY, Osceola Tug Hill XC NY, Ski
Saint-Bruno QC, St. Johann in Tirol AT) plus Granby Ranch gaining cross-country.
Two are report-link-only (`skisaintbruno.ca/en/sliding-conditions`,
`bergbahnen-stjohann.at/de/lifte-und-pisten.html`); Mt. Pisgah and Osceola get
nothing on purpose — neither publishes a snow report at all.

`granby-ranch` was already live here, and like `jay-peak` its published file is
**alpine-side only**, so the nordic half it gained for 26/27 is not represented.

## Fifth announcement — 2026-09-06

Six announced and **all six are new resorts** — the first batch this season with
no existing-card flag flip hiding in it. Elm Creek Park Reserve (Maple Grove MN,
alpine + XC from day one), Sleepy Hollow (Huntington VT, XC), Obertauern and
Petzen (AT), Tschiertschen - Chur (CH) and Snow Resort The Cupid of Romance
(Nagano JP).

All six are report-link-only in the app, and **none of them has an upstream
Liftie parser** — checked all 191 modules in `lib/resorts`. So this batch adds no
pipeline work that can be done today; it is the Node ≥ 23.8 blocker again (the box
runs 22.22), the same one holding up Mont Kanasuta and Eastman.

**Three notes for whoever writes those parsers later:**

- **`kijimadaira.info` is a trap.** OpenSkiMap still records it as the website for
  the Japanese resort, and it is now a **parked domain serving gambling spam** —
  title "Kijimadaira", body linking a 1xbet mirror. The real operator site is
  `kijimadaira-ski.com`, whose ゲレンデ page carries リフト運行状況. The resort is
  the former 木島平スキー場, renamed for the 2023 season under a naming-rights deal.
- **`petzen.net` and Obertauern's lift page are fully JS-rendered.** Every URL on
  petzen.net returns the same 3,867-character nav shell to a scripted client, so
  a parser here needs to find the underlying XHR, not the HTML. Obertauern's
  page is `/winter/liftanlagen.html` ("Offene Lifte & Pisten").
- **Elm Creek is a Three Rivers Park District property**, like the already-live
  `hyland-hills`. Its status lives on the district's shared activity board
  (`threeriversparks.org/page/three-rivers-activity-status`) rather than a
  per-resort page, which means one parser could plausibly cover both — worth
  looking at first, since it is the cheapest of the six.

**One thing in the app repo, not this one, worth knowing here:** Indy's card
coordinate for Sleepy Hollow points at Hamilton County, **New York**, ~200 km from
the Vermont resort. The app now ships the address from the resort's own site and
warns on any US/CA pin that falls outside its state. If anything here ever starts
consuming Indy's coordinates, do not trust them unchecked.

## Sixth announcement — 2026-09-07

Five, all new cards again: Orcières Merlette 1850 (FR), Spring Mountain
Adventures (PA), Winter4Kids / the National Winter Activity Center (NJ), Nutt
Hill (WI) and Veterans Memorial Recreation Area (NH). **No upstream Liftie
parser for any of them** (all 191 modules in `lib/resorts` checked), so again no
pipeline work that clears the Node ≥ 23.8 blocker on a box running 22.22.

**But this batch contains the best parser target of the season.**
`springmountainadventures.com/trail-map/` renders its status **server-side**, as
plain HTML in the page body — not a JS widget, not an XHR:

```
A. Alpine - OPEN          F - Glacier - Closed      1. Terrain Tow Rope - Closed
D. Hawk - Closed          3. Boulder - triple chairlift - OPEN
E. Drifter - Closed       4. Rocktop - double chairlift - Closed
```

Both trails (letters) and lifts (numbers) in one document, each with an explicit
OPEN/Closed. That is a selector away from a real feed, and it is the shape the app
repo's `docs/status-sources.md` has been describing as the missing "HTML-selector
source kind" since the July survey. If one parser gets written this off-season,
this is the one.

Two smaller notes:

- **Veterans Memorial is volunteer-run** (the Franklin Outing Club) and posts
  conditions on `skithevets.org/skiing-and-snowboarding` and Facebook. Indy links
  no website for it at all — the site was found by name.
- **Nutt Hill and Winter4Kids publish no conditions anywhere**, only hours, so
  they get no app entry and would have nothing for a parser to read either.

**And a repeat of the app-side coordinate problem, one batch later:** Indy's card
for Nutt Hill points at Wagner, Charles Mix County, **South Dakota**, ~800 km from
Plymouth, Wisconsin. The app now catches this automatically — a validator warns on
any US/CA pin outside its own state — but the standing note holds: if anything in
this repo ever consumes Indy's coordinates, do not trust them unchecked.

## Feed regressions found while wiring this

Reconciling `status-sources.json` against this repo turned up three entries that
were fetching 404s. Fixed app-side in the same change; noted here because the
first two are Pi-side facts, not app bugs.

- **A caution learned 2026-09-04, before the entries below.** Checking whether a
  file has gone needs the **repo tree**, and the filename the app's `apiURL`
  actually names — which is a **liftie id, not a roster id**, for 82 of the
  pipeline entries. `mountain-high` looked deleted (no
  `status/mountain-high.json`, absent from `_index.json`, raw URL 404) and was
  none of those things: its file is `status/mthigh.json`, healthy, 13 lifts and
  50 trails. In the same session `raw.githubusercontent.com` also served one
  stale 200 for a file that really was gone. Neither a single 404 nor a single
  200 settles it; `git ls-tree` does.
- **`west-mountain` and `white-pass` are gone from the feed.** Absent from
  `status/`, from `_index.json`, from `_health.json` and from `origin/main`'s
  tree, and their raw URLs 404. Both were previously flagged in `docs/resort-parsing-review-2026-07.md`
  for republishing stale spring pages off-season (west-mountain showing 1 lift
  "open" in July; white-pass showing 8/8 lifts and 43/43 trails "open" in
  August), so this looks deliberate. The app entries have been demoted to
  report-link-only, keeping their verified `reportURL`s. **If the removal was
  deliberate, nothing to do. If it was not, these two need their parsers
  restored.**
- **`dog-creek-lodge` publishes as `dog-creek-lodge-nordic-center`.** The file
  is present and healthy (26 trails, last non-empty 2026-09-02) under the
  roster id; the app was still pointing at the old liftie-id filename. App-side
  URL corrected — no Pi-side change needed.
- **67 published FILES are unread by the app — which is about 40 resorts, not
  67.** *(Corrected 2026-09-03; the first version of this bullet said "67
  resorts" and overstated the job.)* The feed carries 250 files;
  `status-sources.json` reads 185. Those 67 unread files collapse to **42
  distinct bundled resorts**, because three multi-area resorts get one file per
  sub-area. Two of the 42 (`saddleback-mountain`, `pebble-creek-ski-area`) are
  already live in the app from their own richer native APIs and are deliberately
  left alone, so **40 would actually gain live status** — 5 of them publishing 0
  rows until the season starts. Mostly European and Japanese: `baqueira-beret`
  (168 rows), `stoten` (112), `palandoken` (60), `pila` (53), `norefjell`,
  `riksgransen`, `kiroro`, `kamui-ski-links`, `geto-kogen`, …

  The file count hid the two reasons this is not a plain
  `Scripts/sync-status-sources.py` run:

  - **Multi-area resorts — RESOLVED APP-SIDE 2026-09-04; nothing to do here.**
    `portes-du-soleil` publishes 10 files (avoriaz, chatel, pds-morzine,
    champery, les-gets, morgins, torgon, abondance, la-chapelle-dabondance,
    saint-jean-daulps), `innsbruck-ski-city-network` 12 (stubai-glacier,
    kuehtai, nordkette, axamer-lizum, schlick-2000, patscherkofel, …) and
    `oberstdorf-kleinwalsertal-bergbahnen` 6 (nebelhorn, fellhorn-kanzelwand,
    ifen, soellereck, walmendingerhorn, heuberg).

    This bullet originally proposed the Pi-side answer — publish a combined
    file per parent so the app could read it unchanged — on the reasoning that
    "the app's config takes one `apiURL` per resort". **That reasoning was
    wrong, and the combined file was rejected.** The app's config takes one
    `apiURL` per KEY, and nothing required a key to be a roster id; its status
    service has always fetched by arbitrary string. So the app now authors the
    membership of each area in its own roster (schema v9 `area` block) and
    reads these 28 files as ordinary entries, one per member.

    The combined file was also the worse product. Summing Portes du Soleil into
    "8 of 208 lifts" answers a question nobody asked: the area exists precisely
    so a passholder can choose WHICH of the twelve to ski, and that choice needs
    per-member counts. The app's card lists the members with their own lifts and
    says outright that it is only hearing from 10 of the 12.

    **What this repo should keep doing:** publish these files exactly as it does
    now, one per sub-area, under their existing ids. Two things would be
    genuinely useful, in this order:
    1. Parsers for **Montriond** and **Val-d'Illiez / Les Crosets /
       Champoussin** — the two Portes du Soleil destinations with no file. The
       app already has rows for them; adding a file plus a `statusID` in the
       roster fills them in with no app change.
    2. Do **not** rename or merge the existing member ids. The roster now names
       them (`area.members[].statusID`), so an id change silently blanks a
       member's row rather than erroring.
  - **Seven do not resolve by website host**, so the generator refuses them by
    design — the same guard that keeps Crystal MI and Crystal WA apart:
    `levi` (feed `levi.fi`, roster `levi.ski`), `corralco` (roster
    `discover.corralco.com`), `aomori-spring`, `hodaigi`, `mount-racey`,
    `tangram-ski-circus`, `leukerbad-torrent`. Each needs a human to confirm the
    id.

  The remaining ~30 are ordinary generator work, and are the part worth doing
  before the season starts.
