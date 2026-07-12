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

## Credits & license

Lift status is collected by [Liftie](https://github.com/pirxpilot/liftie)
(BSD-3-Clause, see [LIFTIE-LICENSE](LIFTIE-LICENSE)). The data itself
originates from the linked resorts' public websites.
