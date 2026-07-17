# Resort parsing review — every source feeding the app (2026-07-17)

An in-depth audit of all lift/trail scraping behind IndiePeaks: the 60 app-facing
Liftie resorts, the 4 published-but-unused status files, the 2 direct-API sources,
and the app-side mapping layer.

**Method.** The production parser set was reproduced locally (liftie fork +
`liftie-patches/0001–0058`; the full 264-test suite passes). Every parser was
then run against (a) its winter fixture and (b) the live page fetched
2026-07-16/17, and diffed against the published `status/*.json` the app
actually downloads. Names and statuses were cross-checked against each
resort's own site (including translation for the 8 Japanese and 3 Austrian
sources), and `web.archive.org` winter snapshots were used where summer pages
hide the winter DOM. Findings below quote exact strings.

**Headline.** 8 resorts are publishing wrong or phantom rows right now,
4 can never produce data until their parser/source is fixed, 2 more look
rotted behind summer pages, and a handful of foreign-language and cosmetic
issues make names/statuses read wrong in the app. The app-side Swift mapper
itself is clean — every user-visible bug originates in the scraped data.

---

> **Update 2026-07-17 — fixes implemented.** Every recommendation below that
> can be fixed from here now ships as `liftie-patches/0059–0077` (19 patches:
> 16 parser/config fixes, a coerce addition, a test-harness helper, and
> formatting). Verified by replicating the production procedure from
> `pi-setup/RESTORE.md`: upstream 4.3.5 + `git am --keep-cr` of all 77
> patches applies cleanly and the full suite passes 269/269. Replaced
> fixtures ship as new `*-2026` files (pure adds) because the old scraped
> fixtures contain CRLF lines that no modify/delete patch can survive
> byte-exactly in both apply modes. Still open, as documented below:
> palcall-tsumagoi (source 403s), caberfae/winterplace and the other
> season-start re-verifications, and the optional publisher stale-open
> guard. `pi-setup/liftie-publish.py` now matches the Pi's resort list
> (rikert, manning-park-xc added). **Apply on the Pi with the normal
> RESTORE.md step; then the next publish cycle replaces the bad data.**

---

## 1 · CRITICAL — wrong or phantom data in the app today

### hoodoo — schedule table parsed as live status
- Source: `https://skihoodoo.com/the-mountain/mountain-lift-status/`
- `#tablepress-10` is a static **LIFT | HOURS schedule**, not a status table.
  The parser (`selector: '#tablepress-10 tr'`, `status: s === 'CLOSED' ? 'closed' : 'open'`)
  therefore reports every lift with posted hours as **open**, year-round:
  published July data shows **6 of 7 lifts open** at a summer-closed resort.
- The `<thead>` row is also matched: header cells `LIFT | HOURS` become a
  phantom lift literally named **"LIFT"**, status open.
- The page's own footnote says "Lift schedule is what we plan to open" — there
  is no real-time status on this page.
- Fix: switch to `#tablepress-10 tbody tr` (kills the phantom) and map
  hours → `scheduled`, `CLOSED` → `closed` — or, more honestly, drop hoodoo to
  report-link-only like cannon, since the source has no live status at all.

### red-lodge-mountain — every lift collapses into one phantom "Chair Status"
- Source: `https://www.redlodgemountain.com/mountain/snow-report/`
- The site restructured its rows. `.chair-header.row` still matches all
  7 lift rows, but the first text inside each is now the label
  `<h3>Chair Status</h3>`, and the status icon moved. All 7 rows parse to the
  same name, overwrite each other, and the app shows **one lift named
  "Chair Status", status `scheduled`** (missing alt → coerce fallback).
- Verified live: the real name now lives in `.chair-header-right h2`
  (e.g. "Magic Carpet") and the status in the `.chair-status` div's class /
  `img.sr-icon[alt]` (`closed`).
- Fix (parser rewrite):
  `name: row → findText(select(row.children, '.chair-header-right h2')[0])`,
  `status: select(row.children, '.chair-status .sr-icon')[0]?.attribs.alt`.
- Bonus: the page now also carries per-run tables (Run | Level | Groomed |
  Status) — a trails parser could be added for free while in there.

### 49-degrees-north — configured host no longer exists
- `resort.json` fetches `https://new.ski49n.com/mountain-info/trail-status`;
  **`new.ski49n.com` no longer resolves** (connection fails), while
  `https://www.ski49n.com/mountain-info/trail-status` responds 200.
- The resort has published empty data ever since tracking began and will stay
  empty forever, silently, including all next winter.
- Fix: point `resort.json` at `www.ski49n.com` and re-verify the selector
  against the winter page at season start.

### mthood (Mt Hood Meadows) — page moved, selector extinct
- `/the-mountain/conditions` now 308-redirects to
  `https://www.skihood.com/mountain-report`; the parser's `#liftGrid` does not
  exist anywhere on the new page. Empty since tracking began.
- Fix: rebuild the parser against the new page (check for embedded JSON/API it
  hydrates from), or drop to report-link-only until rebuilt.

### owlshead — redesign killed the parser before last season
- Parser anchors on `.legende_title:contains(Lifts)`. The live page has **no
  `legende_*` classes at all — and neither does the 2026-01-21 winter
  snapshot** on web.archive.org. So this produced nothing all last season.
- Fix: rebuild from the current `owlshead.com/en/ski-conditions/` DOM. Note the
  page is bilingual (FR/EN); `coerce` already handles ouvert/fermé if the new
  selector surfaces French statuses.

### palcall-tsumagoi — source started blocking on 2026-07-16
- `https://tsumagoiskiresort.life/` now returns **HTTP 403** to the scraper;
  `_health.json` shows the resort went empty at 12:30 UTC the same day.
- Also worth confirming this `.life` domain is still the resort's canonical
  home before investing in a fix (it is not the historical `palcall.co.jp`).
- Fix: adjust User-Agent / fetch approach if the block is UA-based, find the
  official replacement page, or drop to report-link-only.

### chinapeak — footnote rows published as lifts
- The `.row.chair-bar` selector matches two non-lift rows the site renders in
  lift markup, so the app shows lifts named **"*"** and **"Tubing Hill Not
  Available This Season"** (both "closed").
- The name function `s.trim().slice(0, -1)` blindly strips the trailing colon —
  `"*: "` → `"*"` — and would corrupt names if the site ever drops the colon.
- Fix: filter rows (`name.length > 1 && !/not available/i.test(name)`), and
  make the colon-strip conditional (`s.replace(/:\s*$/, '')`).

### castle-mountain — terrain parks listed as lifts (and double-counted)
- The lift parser excludes trail rows by difficulty icon
  (`/circle|square|diamond/i`) — but terrain-park rows carry a *park* icon, so
  **"Meadows S/M Park"** and **"Tumbleweed Terrain Park"** pass the filter and
  are published as lifts, while the trails parser also (correctly) lists them
  as trails. Lift total reads 9 instead of 7.
- Fix: extend the exclusion to `/circle|square|diamond|terrain|park/i`.

### eagle-point — "Terrain Parks" section heading published as a lift
- The lift selector is the section-heading row (`tr.label-status-row`) of the
  grouped runs table. One of those headings is **"Terrain Parks"** — a trail
  group, not a lift — so the app shows 6 lifts where Eagle Point has 5.
- Fix: skip that heading by name (`if (name === 'Terrain Parks') return;`).

### big-moose — difficulty suffixes leak into names, with the wrong level
- The trail level comes from GoDaddy menu *section titles* ("Green Circle
  Trails…"). The "Upper Mountain (Advanced Backcountry Terrain)" section maps
  to `doubleBlack`, but the resort annotates individual items there with their
  real rating, so the app shows trails literally named **"Upper Penobscot -
  Blue Square"**, **"East Branch - Blue Square"**, **"St Croix - Black
  Diamond"**, **"Moose River - Black Diamond"**, **"Piscataquis (The Cat) -
  Black Diamond"** — each marked **doubleBlack**.
- Fix: strip a trailing `/\s*-\s*(green circle|blue square|black diamond|double black.*)$/i`
  from the name and use it to override the section level.

### greek-peak — duplicated trails (selector matches two tables)
- The page contains **two** `#gp-trail-table` tables (day/night); the selector
  matches both, so 7 trails are published twice each ("Keres", "Medusa",
  "Lower Thanatos", "Down & Dirty", "Spartan", "Nemesis", "Trident") — 79 rows
  where the page has 72 unique.
- "Back N' Double Black" looks like an artifact but is a **real trail name**
  (literal page text) — leave it alone.
- The 19 trails showing "open" in July are the resort's own stale CSS classes
  (`trail-open`), not a parse error — see §3.
- Fix: parse only the first `#gp-trail-table`, or dedupe by name (merge:
  open-wins).

### sasquatch-mountain — CMS junk row published as a lift
- The intermaps feed (`skiron.intermaps.com/get_data.asp`) contains an
  unfinished object literally named **"new object by hemlock_resort"**, which
  passes the `ELEMENTGROUP[NAME="LIFT"]` filter and is published as a lift.
- Unknown status codes fall through `code2status` → `undefined` → `scheduled`
  silently.
- Fix: filter `/^new object/i` names; log-and-skip unknown status codes.
  (The "A- / B- / D-" name prefixes are the feed's own naming; harmless.)

---

## 2 · LIKELY BROKEN — hidden behind summer pages, verify at season start

| resort | evidence | recommended action |
|---|---|---|
| **caberfae-peaks** | old URL redirects to new `/snow-report/`; the parser's `#tablepress-4` exists nowhere on the new page | re-scout selector before winter |
| **winterplace** | `www.` host redirects to apex; positional selector `.row:nth-child(n + 7) td:nth-child(2n + 1)` finds nothing (page has 5 `.row`s); this selector style breaks on any layout edit | rewrite with a structural selector |
| **canaan-valley** | per-difficulty `div.beginner/more-difficult/most-difficult` tables absent from the summer page (only an icon class remains) | confirm tables return in winter |
| **snow-ridge** | hand-posted table currently has no data rows / no "Lift Report" marker | confirm at season start |
| **ragged-mountain** | `table.slope` still present, but selector hardcodes the **last 5 rows** (`tr:nth-last-child(-n + 5)`) — breaks the moment a row is added/removed | replace with a row-content filter |
| **bolton-valley** | `admin-ajax.php?action=get_prop_conditions` currently returns **invalid JSON** (dangling commas from the PHP template) → clean empty; likely valid again when populated | spot-check in December |
| **shawnee-mountain** | `wp-json/shawnee-widget/v1/weather/` returns 403 to this review environment; production has published no data since tracking began (2026-07-12) | check Pi logs for 403s; verify in winter |
| **pats-peak** | `services.patspeak.com/api/SnowReport/Status` 403 to this environment; same caveat as shawnee | same |

(`takasu-snow-park` and `washigatake` were also empty, but their pages still
contain the `リフト名` table header the parser keys on — genuinely
summer-empty, parsers healthy.)

## 3 · STALE SOURCE — parser faithful, resort's own data wrong

These look like bugs in the app but the scraper is accurately mirroring what
the resort publishes:

- **king-pine** — the vicomap API (`/api/details/821`) still returns
  `Open` for 4 of 5 lifts in mid-July; the resort never flipped its feed after
  closing. (The null-status "Tubing Park Tow" is correctly skipped.)
- **west-mountain** — showed 12 of 36 trails open on the morning of
  2026-07-16 (the resort's own table values; all closed again by evening).
  Its difficulty column also labels "The North Face" *Green* — their data.
- **greek-peak** — 19 `trail-open` CSS classes on the July page (see §1).
- **hoodoo** — even after the parser fix, the source only publishes a plan,
  not live status.
- Smaller cases: big-moose (6 trails/1 lift "open" in July), berkshire-east
  (Summit Quad open — actually *true*: summer downhill MTB), glencoe &
  pitztaler & hochzeiger & lutsen summer "open"s are real summer operations.
- **Optional guard:** the publisher could flag resorts reporting open lifts
  between May–October for manual review, so stale feeds like King Pine don't
  ride into the app unnoticed for months.

## 4 · Foreign-language sources — what each status/name really says

- **nayoro-piyashiri** — all 13 trails show **`hold`** because the page marks
  every course `STANDBY` (their off-season label) and `coerce` maps
  `standby → hold` explicitly. Lifts on the same page say `運休` (suspended)
  → closed, which is right. Recommendation: treat `STANDBY` as `closed` (or
  `scheduled`) in `nayoro-piyashiri/status.js` — "hold" reads as a wind-hold
  in the app, which is misleading off-season.
- **togakushi** — trail names keep their difficulty parenthetical, e.g.
  **「お仙水コース（初級者）」**, duplicating the level chip the app already
  shows — and **「とがっきーC（初心者）」 gets *no* level at all** because the
  section mapper knows 初級 (beginner) but not 初心者 (novice). Fix: map
  初心/初級 → green and strip the `（…）` suffix from display names.
  (Everything else translates sensibly: 中級→blue ✓, 上級→black ✓,
  ポール専用 "poles/race only" and 中央バーン "central face" correctly
  carry no level.)
- **dynaland / takasu-snow-park / washigatake / hirugano-kogen** — shared
  glyph translator handles `○/◯/〇` and 運行中/営業中 → open, `△/▲` → hold,
  `×/✕/✖/-` and 運休/終了 → closed. Header row is skipped by design
  (リフト名-keyed table detection). Verified clean; names are real lift/course
  names (第1クワッド, からまつビギナーリフト, 林間コース, …).
- **okunakayama** — lift numbering on the page genuinely skips 第2リフト
  (they list 第1,3,4,5,6) — not a parse gap.
- **palcall-tsumagoi** — see §1 (403).
- **pitztaler-gletscher (DE)** — names arrive as the site prints them:
  **"GLE || Gletscherexpress"**, **"RIFF || 1 Rifflsee Talabfahrt"**. The
  `GLE ||` / `RIFF ||` area prefixes are on-page text, not parser damage —
  but they read terribly in the app. Recommend stripping
  `/^(GLE|RIFF)\s*\|\|\s*/` (optionally re-appending "· Gletscher" /
  "· Rifflsee"). Statuses (colored-dot classes) verified; the 3 July "open"
  lifts (Gletscherexpress, Wildspitzbahn, Rifflseebahn) are real summer
  sightseeing operations.
- **skiwelt (DE)** — the trails come from SkiWelt's own facility API filtered
  to `typeIDs=2`, which returns **only piste-type items** (verified live:
  42 easy, 42 medium, 5 difficult, 11 skiroute). Rows named
  **"Kaiserexpress"×3 / "Köglbahn"×3 / "Zauberteppich …"** are SkiWelt's names
  for the piste *segments beside those lifts*, not lifts leaking through — but
  ~15 duplicate titles inflate the count (100 rows ≈ 85 unique pistes).
  Recommend deduping by title (open-wins). `skiroute → doubleBlack` is a
  reasonable judgment call; keep.
- **hochzeiger (DE)** — same API family, same behavior; off-season rows carry
  no `state` and are correctly dropped. 9 lifts verified real
  (Gondelbahn, Zirbenbahn, …); July "open"s are genuine summer lifts.
- **glencoe (Scotland)** — status images `0/1/2.jpg` mapped closed/hold/open;
  the `1.jpg → hold` reading is an assumption worth confirming with a winter
  page, but current output (2 open summer-sightseeing chairs) matches reality.
- **owlshead (FR/EN)** — see §1 (rot).

## 5 · MINOR — cosmetic, duplicates, hardening

- **lutsen-mountains** — icon title **"Projected"** isn't in `coerce`'s map,
  so it lands on `scheduled` only via the unknown-fallback. Right answer by
  accident; add `projected: 'scheduled'` explicitly. ("Ullr Chair" vs
  "Ullr (Nordic)" are genuinely two rows on the page; keep.)
- **mt-abram** — "Mahoosuc Meadow" and "Easy Rider to Rough Rider" each appear
  twice in output (repeated across the page's report grids). Dedupe by
  name+status.
- **burke-mountain / granite-peak** — "Deer Run" (Burke) and
  "Meadows"/"Mystery"/"Whitetail" (Granite) are duplicated *on the resorts'
  own pages* (two sections). Harmless; optional dedupe.
- **snowriver** — the page itself lists **"Draw Stroke" as both a lift and a
  trail** (canoe-themed naming; likely a handle tow and its run) and spells
  **"Birgantine"** that way. Faithful mirror; no action.
- **wisp / ski-sawmill** — activity rows ("Mountain Coaster", "Snow Tubing")
  ride along in the trail lists because the resorts put them in the same
  tables; they inflate trail totals by 1–2. Filter if the counts bother you.
- **saskadena-six** — four "UPHILL - …" skinning routes are counted as trails
  (they are rows on the resort's page). Acceptable; filter optional.
- **mission-ridge** — 57 rows include named roads/cat-tracks ("Road to
  Chair 3", "Tower 10", "Bomber Access Road") — all real rows on their report.
- **cataloochee** — "Wolf Creek ( Conveyor)" spacing comes from the page
  markup; cosmetic only.
- **swain** — generic lift names ("Quad 1/2/3, Double Chair, Magic Carpet")
  are exactly what the resort's table says. Not a swap.
- **sundown-mountain** — "Sun Express" is a real blue-square **trail** on the
  resort's own report (its lifts are unnamed); lifts are intentionally not
  scraped because the page has no lift table. Correct as-is.
- **echo-mountain** — `projected.svg → scheduled` handled explicitly ✓; page
  has no difficulty markers, hence level-less trails (same for wisp,
  wintergreen, saskadena-six, and the Japanese pages except togakushi).
- **wintergreen** — "Big Acorn", "Potato Patch", "Loggers Alley" in both lift
  and trail lists are correct: Wintergreen names lifts after trails. Verified
  against their page structure (separate lift/trail tables).
- **loveland** — the `'-'`-split parse holds for all current names; would
  corrupt any future lift name containing a hyphen. Hardening note only.

## 6 · Engine-level patterns behind these bugs (liftie fork)

1. **Unknown statuses silently become `scheduled`** (`lib/tools/coerce.js`).
   Every foreign or novel label that misses the map degrades invisibly
   (Lutsen "Projected"; Red Lodge's missing alt). Consider logging a
   per-resort "unknown status" counter into `_health.json` to surface these.
2. **`collect()` keeps any selector match with a non-empty name**
   (`lib/tools/domutil.js`) — this is what turns header/footnote rows into
   phantom lifts (hoodoo "LIFT", chinapeak "*", eagle-point "Terrain Parks").
   Prefer `tbody`-scoped selectors and name filters in every new parser.
3. **No dedupe anywhere in the trails pipeline** — duplicate rows flow
   straight into the app (greek-peak, skiwelt, mt-abram).
4. **Silent-empty rot** — when a site redesigns, parsers return `{}` with no
   error (49-degrees-north, mthood, owlshead each went dark unnoticed).
   `_health.json`'s `emptyButPreviouslyPopulated` only catches transitions
   after 2026-07-12. Recommend a season-start checklist (re-run this review's
   live sweep in late November) and an alert if a resort stays empty through
   December–March.

## 7 · Publisher & repo housekeeping

- `pi-setup/liftie-publish.py` in this repo does **not** include `rikert` and
  `manning-park-xc`, yet both are being published (the Pi runs a newer list) —
  commit the current list back to the repo.
- **Published but unused by the app:** `cannon.json` (parser 404s — correctly
  report-link-only in the app), `saddleback.json` (stale Liftie copy; the app
  uses the Netlify API instead — delete or stop publishing),
  `rikert.json` + `manning-park-xc.json` (parse fine — "Unnamed Trails" at
  Rikert is genuine Nordic Pulse data — but no app entry references them;
  either wire them into `status-sources.json` or drop them).

## 8 · Direct APIs and the app-side mapper — verified clean

- **saddleback (Netlify)** — `data.lifts` is a *dictionary keyed by name*;
  the Swift mapper explicitly handles dict-of-objects, trims Saddleback's
  trailing-space names ("Rangeley "), maps `FORECAST → scheduled`, and knows
  both level vocabularies (`GREEN_CIRCLE…` and `green/doubleBlack…`). ✓
- **pebble-creek** — API fields present (`TrailsOpen: "0"` string is coerced;
  `Comments: "Closed for the Season"`). ✓
- **ResortStatusMapper.swift** — no lift/trail swaps, no counting of
  hold/scheduled as open, sum-paths require every part (no silent
  undercount), unknown item states render as `.unknown` rather than open. The
  phantom rows users see (e.g. "Chair Status") are rendered verbatim from the
  data — fixing the parsers fixes the app.

## 9 · Per-resort verdict table (60 app-facing)

| verdict | resorts |
|---|---|
| **BROKEN (fix parser/source)** | hoodoo · red-lodge-mountain · 49-degrees-north · mthood · owlshead · palcall-tsumagoi · chinapeak · castle-mountain · eagle-point · big-moose · greek-peak · sasquatch-mountain |
| **verify at season start** | caberfae-peaks · winterplace · canaan-valley · snow-ridge · ragged-mountain · bolton-valley · shawnee-mountain · pats-peak |
| **stale source (resort's data)** | king-pine · west-mountain (intermittent) |
| **minor / cosmetic** | pitztaler-gletscher · skiwelt · togakushi · nayoro-piyashiri · lutsen-mountains · mt-abram · glencoe · wisp · ski-sawmill · saskadena-six · cataloochee · loveland |
| **OK (verified)** | berkshire-east · big-white · bolton-valley* · burke-mountain · calabogie · cooper-spur · donner-ski-ranch · dynaland · echo-mountain · glencoe* · granite-peak · hirugano-kogen · hochzeiger · jay-peak · king-pine* · little-switzerland · loveland* · lutsen-mountains* · manning-park · mission-ridge · mt-abram* · mt-la-crosse · mthigh · nordic-mountain · okunakayama · saskadena-six* · snowriver · sundown-mountain · swain · takasu-snow-park · togakushi* · washigatake · waterville · west-mountain* · wintergreen · winterplace* · wisp* |

\* appears in two rows: parser structurally sound (OK) with the listed caveat.

Fixture note: parsers marked OK were verified against both the winter fixture
and the live page; summer-empty resorts (takasu, washigatake, …) were verified
to still have the DOM structure their parser keys on.
