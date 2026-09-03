# Status recon — the resorts Indy added for 2026-27

**Date: 2026-09-02, extended 2026-09-03.** Written while adding the 26/27 partners to the IndiePeaks
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

## Feed regressions found while wiring this

Reconciling `status-sources.json` against this repo turned up three entries that
were fetching 404s. Fixed app-side in the same change; noted here because the
first two are Pi-side facts, not app bugs.

- **`west-mountain` and `white-pass` are gone from the feed.** Absent from
  `status/`, from `_index.json` and from `_health.json`, and their raw URLs
  404. Both were previously flagged in `docs/resort-parsing-review-2026-07.md`
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

  - **Multi-area resorts.** `portes-du-soleil` publishes 10 files here
    (avoriaz, chatel, pds-morzine, champery, les-gets, morgins, torgon,
    abondance, la-chapelle-dabondance, saint-jean-daulps),
    `innsbruck-ski-city-network` 12 (stubai-glacier, kuehtai, nordkette,
    axamer-lizum, schlick-2000, patscherkofel, …) and
    `oberstdorf-kleinwalsertal-bergbahnen` 6 (nebelhorn, fellhorn-kanzelwand,
    ifen, soellereck, walmendingerhorn, heuberg). The app's config takes one
    `apiURL` per resort, so wiring any single sub-area would show Avoriaz's
    lifts as the whole of Portes du Soleil. **This is the one thing that might
    want a Pi-side answer**: publishing a combined file per parent resort would
    let the app read them as-is, and is probably cheaper than extending the
    app's schema to sum several sources.
  - **Seven do not resolve by website host**, so the generator refuses them by
    design — the same guard that keeps Crystal MI and Crystal WA apart:
    `levi` (feed `levi.fi`, roster `levi.ski`), `corralco` (roster
    `discover.corralco.com`), `aomori-spring`, `hodaigi`, `mount-racey`,
    `tangram-ski-circus`, `leukerbad-torrent`. Each needs a human to confirm the
    id.

  The remaining ~30 are ordinary generator work, and are the part worth doing
  before the season starts.
