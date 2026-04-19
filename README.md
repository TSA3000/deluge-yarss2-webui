# YaRSS2 v2.2.1 — Deluge RSS plugin with WebUI

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](./LICENSE)
[![Deluge: 2.x](https://img.shields.io/badge/Deluge-2.x-purple.svg)](https://deluge-torrent.org/)
[![Python: 3.6+](https://img.shields.io/badge/Python-3.6%2B-green.svg)](https://www.python.org/)

A security, correctness, and feature release of the **YaRSS2** plugin for
Deluge 2.x, with a complete **WebUI** configuration interface.

Watches RSS feeds, filters entries with regex, and auto-adds matching torrents
to Deluge — configurable from either the GTK client or (new in this release)
the WebUI.

## What's in this fork

This release brings YaRSS2 current with security best practices and adds
first-class WebUI support. Previous versions required the GTK client for any
non-trivial configuration; this one lets you manage feeds, subscriptions, and
cookies entirely through the browser-based WebUI.

### Highlights

- **TLS verification restored** on torrent file downloads (was hardcoded off).
  Per-feed opt-out available for self-signed trackers.
- **Proper cookie hostname matching** — previous substring match would leak
  cookies from `example.com` to `notexample.com`.
- **Complete WebUI CRUD** — five-tab preferences page for Feeds, Subscriptions,
  Cookies, General settings, and a live Log viewer. No more "use the GTK
  client" notice.
- **ETag / If-Modified-Since caching** — don't re-parse feeds that haven't
  changed since last poll.
- **Configurable concurrency** — run feed fetches in parallel
  (`max_concurrent_feeds`).
- **Size-parser fix** covers KB/MB/GB/TB and binary variants (MiB, GiB, etc.).
- **Email notification scope bug** fixed.
- **Duplicate-infohash resilience** — one add failure no longer aborts the
  entire batch.
- **Config schema v9** — new fields added with safe defaults; downgrading to
  2.1.x remains non-destructive.

See [`CHANGELOG.md`](./CHANGELOG.md) and [`RELEASE_NOTES.md`](./RELEASE_NOTES.md)
for the full list of changes.

## Credits

- **Original author:** Camillo Dell'mour (YaRSS, 2009)
- **v1.x–v2.1.x maintainer:** bendikro (2012–2021)
- **v2.2.x maintainer:** Sam Mahdi (2026)

Retains the GPLv3 license and all prior copyright notices. See
[`LICENSE`](./LICENSE) for license text and [`CHANGELOG.md`](./CHANGELOG.md) for
the complete authorship history.

## Requirements

- **Deluge 2.x** (tested with 2.2.0 on Ubuntu 24.04, libtorrent 2.0.10)
- **Python 3.6+** on the Deluge daemon. The egg must be built against the same
  Python version your Deluge daemon runs.

YaRSS2 v2.x does **not** support Deluge 1.3.x.

## Installing

YaRSS2 ships as a Python egg that Deluge loads at startup. **The egg must be
built against the same Python version that your Deluge daemon uses**,
otherwise Deluge will silently fail to load it.

### Option A: use a prebuilt egg

Download the egg matching your Deluge's Python version from the
[Releases](https://github.com/TSA3000/deluge-yarss2-webui/releases) page, then:

```bash
# Adjust path for your Deluge user
sudo cp YaRSS2-2.2.1-py3.12.egg /var/lib/deluge/.config/deluge/plugins/
sudo chown deluge:deluge /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.1-py3.12.egg
sudo chmod 644 /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.1-py3.12.egg
sudo systemctl restart deluged deluge-web
```

On Windows (Deluge bundled with its own Python) the plugin folder is typically:

```
%APPDATA%\deluge\plugins\
```

### Option B: build from source

```bash
git clone https://github.com/TSA3000/deluge-yarss2-webui.git
cd deluge-yarss2-webui
python3 setup.py bdist_egg
# Resulting egg is in ./dist/
```

Then copy the egg to your Deluge plugins directory as above.

### Enable in Deluge

1. Open Deluge (GTK client) or Deluge WebUI.
2. **Preferences → Plugins** (GTK) or **Preferences → Plug-ins** (WebUI).
3. Tick **YaRSS2**. A new **YaRSS2** entry appears in the Preferences sidebar.

## Quick start (WebUI)

1. **Preferences → YaRSS2 → RSS Feeds tab**. Click **Add**.
   Fill in Name, URL, keep Update interval at 30 minutes, keep "Verify TLS
   certificate" ticked. Save.
2. **Subscriptions tab**. Click **Add**. Pick your feed. Give it a name,
   enter a regex in "Regex include", e.g.
   `^Show Name S\d+E\d+ 1080p`. Optionally set "Move completed to". Save.
3. **RSS Feeds tab → select your feed → Run now** to trigger an immediate
   fetch. Check your Deluge main view — matching torrents should appear.

## Upgrade notes from v2.1.x

- Config auto-migrates from v8 → v9 on first load. No user action required.
- The new `verify_tls` feed option defaults to `True`. If you were relying on
  broken TLS verification (probably unintentional), untick it per-feed.
- The new `max_concurrent_feeds` general option defaults to `1` (previous
  hardcoded behavior). Raise it if slow feeds block faster ones.

## Known limitations

Deferred from this release (still configurable via the GTK client):

- Email message templates editor
- Tri-state torrent options UI (ask Deluge default / force true / force false)
- Path autocomplete in Download location / Move completed fields
- Regex live-preview in subscription editor

These settings round-trip correctly when editing through the WebUI — they're
preserved from whatever values the GTK client set.

## Troubleshooting

**Plugin doesn't load.** Check that the Python version suffix on the egg
matches your Deluge's Python (e.g. `py3.12`, `py3.13`). Deluge fails silently
on a mismatch. Check `~/.config/deluge/deluged.log` for import errors.

**"Run now" says "not modified" and does nothing.** Fixed in v2.2.0 —
user-triggered runs bypass the ETag cache. If you see this on v2.2.x, the
egg may be stale; redeploy the latest.

**Nothing downloads.** Verify the `move_completed` path exists and is writable
by the Deluge user:

```bash
sudo -u deluge test -w /your/move/completed/path && echo OK || echo MISSING
```

Create it if missing. Deluge rejects adds with nonexistent move paths.

**Feed save "loses" the selected feed in a subscription.** Fixed in v2.2.0.
If you see this, you're on a cached JS build. Hard-refresh the browser with
DevTools → Network → "Disable cache" → Ctrl+Shift+R.

## Contributing

Pull requests welcome. The code style follows what was already in the tree:
Python 3, PEP 8-ish, 4-space indentation. The WebUI is ExtJS 3 (that's what
Deluge's WebUI uses) in a single file: `yarss2/data/yarss2.js`.

Tests live in `yarss2/tests/`. The regression tests added for v2.2.0 are in
`test_v9_fixes.py`.

## License

GPLv3 — see [`LICENSE`](./LICENSE).
