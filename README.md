# IndiePeaks Lift Status Data

Ski lift status JSON for the IndiePeaks iOS app.

## What this is

Each file under `status/` holds the lift status for one resort, keyed by its
[Liftie](https://github.com/pirxpilot/liftie) resort id
(e.g. `status/loveland.json`). The data is scraped from the resorts' public
lift-status pages by a self-hosted Liftie instance and published here.

The app fetches these files from
`https://raw.githubusercontent.com/orlandocastiglioni/indiepeaks-lift-status/main/status/<id>.json`.

## Update cadence

A publisher checks the local Liftie instance every **15 minutes** and commits a
file **only when that resort's lift status actually changed**. The top-level
`fetchedAt` field (UTC, ISO-8601) is therefore "when this status last
changed", not "when it was last checked". Off-season, files can go unchanged
for months — that is normal.

## File format

The full Liftie API response for the resort, plus `fetchedAt`. The interesting
part is `lifts`:

```json
{
  "fetchedAt": "2026-07-12T14:00:00Z",
  "lifts": {
    "status": { "Chet's Dream": "closed" },
    "stats": { "open": 0, "hold": 0, "scheduled": 0, "closed": 10,
               "percentage": { "open": 0, "hold": 0, "scheduled": 0, "closed": 100 } }
  }
}
```

Lift states are `open`, `closed`, `hold`, or `scheduled`. Off-season the
`status` map may be empty and stats all zero.

Resorts whose pages carry per-trail rows also publish a top-level `trails`
object: `stats` with the same four states, and `list` — an array of
`{name, status, level?}` objects when the page shows difficulty markers
(`level` is `green`, `blue`, `black`, `doubleBlack`, or `terrainPark`),
or a plain `{name: status}` map when it doesn't. Trails-only resorts
(e.g. calabogie, canaan-valley) have no `lifts` key at all.

## Notes on the data set

`docs/` carries the dated audits behind this feed:

- `resort-parsing-review-2026-07.md` — a per-parser review of every source.
- `new-resorts-2026-27-recon.md` — why the six resorts Indy added for 26/27 have
  no parser yet, what each of their sites actually publishes, and the feed
  regressions (`west-mountain` / `white-pass` gone; `dog-creek-lodge` publishing
  under its roster id) found while wiring them.

## Credits & license

Lift status is collected by [Liftie](https://github.com/pirxpilot/liftie)
(BSD-3-Clause, see [LIFTIE-LICENSE](LIFTIE-LICENSE)). The data itself
originates from the linked resorts' public websites. Sites that render
their reports with JavaScript or sit behind Cloudflare are fetched through
a headless-chromium tier (FlareSolverr / renderd — see
[pi-setup/RESTORE.md](pi-setup/RESTORE.md)).

## Multi-resort areas

Three of the app's resorts are not one mountain but a group of separately-run
resorts sharing one Indy Pass listing, and this feed publishes **one file per
member**:

| App resort | Members published here |
|---|---|
| Portes du Soleil | `abondance`, `avoriaz`, `champery`, `chatel`, `la-chapelle-dabondance`, `les-gets`, `morgins`, `pds-morzine`, `saint-jean-daulps`, `torgon` |
| Innsbruck Ski & City Network | `axamer-lizum`, `elferbahnen`, `glungezer`, `hochoetz`, `kuehtai`, `muttereralm`, `nordkette`, `patscherkofel`, `rangger-koepfl`, `schlick-2000`, `serlesbahnen`, `stubai-glacier` |
| Oberstdorf Kleinwalsertal Bergbahnen | `fellhorn-kanzelwand`, `heuberg`, `ifen`, `nebelhorn`, `soellereck`, `walmendingerhorn` |

Since 2026-09-04 the app reads all 28 of these and totals them itself, listing
each member with its own lift count. **These ids are named in the app's bundled
roster**, so renaming or merging one silently blanks that member's row instead
of failing loudly — treat them as a published interface. The parent resorts
(`portes-du-soleil` and friends) have no file here and need none. The
`(Portes du Soleil)` suffix in `_index.json` is a display name only; the app
does not parse membership out of it.

Missing, and worth a parser if the sources allow: **Montriond** and
**Val-d'Illiez / Les Crosets / Champoussin**, the two Portes du Soleil
destinations with no file. The app already shows a row for each, marked as
unreported.

## Index

`status/_index.json` lists every published resort id with its display name —
apps can discover newly added resorts from it instead of shipping their own
list. `status/_health.json` records per-resort row counts and the last time
each resort had data (empty in summer is normal; `lastNonEmpty` shows the
last real report).
