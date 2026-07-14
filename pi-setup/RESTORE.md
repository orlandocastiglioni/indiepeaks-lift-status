# Rebuilding the Liftie pipeline from a blank SD card

Everything needed to resurrect the self-hosted Liftie → IndiePeaks publish
pipeline lives in this repo: this directory (units + scripts) and
`../liftie-patches/` (every local commit on top of upstream Liftie).

Target: Raspberry Pi, 64-bit Raspberry Pi OS (aarch64 — check with `uname -m`),
user `orlando` with sudo. Adjust paths if the user differs.

## 1. Node.js 24 (NodeSource) + pnpm 10

```sh
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo bash -
sudo apt-get install -y nodejs git
sudo corepack enable && corepack prepare pnpm@10 --activate
```

Liftie needs Node >= 23.8 (URLPattern). pnpm must be major 10 — 11 rejects
upstream's lockfile.

## 2. Liftie checkout + local patches

```sh
git clone https://github.com/pirxpilot/liftie ~/liftie
cd ~/liftie
git checkout 546d615        # upstream base the patches apply to (Release 4.3.5)
git config user.email orlando@orlandocc.me
git config user.name "Orlando Castiglioni"
git am --keep-cr ~/lift-status-data/liftie-patches/*.patch
make build                  # pnpm install + client asset build
make test                   # should be all green
```

`--keep-cr` matters: some test fixtures are scraped pages with CRLF lines,
and plain `git am` would strip the CRs (verified: with the flag the result
is byte-identical to the source tree).

```sh
```

(Clone this data repo first if you haven't: step 3.)

If upstream has moved and the patches no longer apply to `main`, applying
them onto 546d615 as above always works; rebase at your leisure.

## 3. Data repo + push credential

```sh
git clone https://github.com/orlandocastiglioni/indiepeaks-lift-status ~/lift-status-data
cd ~/lift-status-data
git config user.email orlando@orlandocc.me
git config user.name "Orlando Castiglioni"
git config credential.helper "store --file /home/orlando/.git-credentials-liftie"
```

Create `/home/orlando/.git-credentials-liftie` containing exactly one line —
`https://orlandocastiglioni:<FINE-GRAINED-PAT>@github.com` — where the PAT is
a GitHub fine-grained token with push access to `indiepeaks-lift-status`
(generate a fresh one at github.com → Settings → Developer settings). Then:

```sh
chmod 600 /home/orlando/.git-credentials-liftie
git push origin main   # dry check: should say "Everything up-to-date"
```

Never commit this file or paste the token anywhere.

## 4. Publish + watchdog scripts

```sh
cp ~/lift-status-data/pi-setup/liftie-publish.py ~/lift-status-data/pi-setup/liftie-watchdog.py ~/
chmod +x ~/liftie-publish.py ~/liftie-watchdog.py
```

## 5. systemd units

```sh
sudo cp ~/lift-status-data/pi-setup/liftie.service \
        ~/lift-status-data/pi-setup/liftie-publish.service \
        ~/lift-status-data/pi-setup/liftie-publish.timer \
        ~/lift-status-data/pi-setup/liftie-watchdog.service \
        ~/lift-status-data/pi-setup/liftie-watchdog.timer /etc/systemd/system/
```

Edit `/etc/systemd/system/liftie-watchdog.service` and replace
`NTFY_TOPIC=<your-private-ntfy-topic>` with the real topic (kept out of this
public repo; it's set in the watchdog unit on the running Pi — or pick any
new random private string and subscribe your phone to it at ntfy.sh).

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now liftie.service liftie-publish.timer liftie-watchdog.timer
```

Note: `liftie.service` binds 127.0.0.1:3001 (3000 is taken by the homepage
container on the old Pi; on a blank Pi you could use 3000, but then update
`LIFTIE` in liftie-publish.py — simpler to keep 3001).

## 6. Verify end-to-end

```sh
curl -s localhost:3001/api/resort/loveland | head -c 300   # JSON with "lifts"
python3 ~/liftie-publish.py                                # publishes changes
cat ~/lift-status-data/status/_health.json                 # fresh lastRun
python3 ~/liftie-watchdog.py                               # "watchdog: all healthy"
systemctl list-timers 'liftie*'                            # both timers scheduled
```

The resort roster lives in TWO places that must stay in sync: the
`LIFTIE_RESORTS` env in `liftie.service` and `RESORTS` in `liftie-publish.py`.
