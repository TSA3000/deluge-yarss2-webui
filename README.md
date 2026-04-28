<p align="center">
  <img src="docs/images/yarss2-128.png" alt="YaRSS2 logo" width="96">
</p>

# YaRSS2 v2.2.5 — Deluge RSS plugin with WebUI

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
- **Floating window UI** — open YaRSS2 in a free-standing, resizable, draggable
  window from the new toolbar button or by clicking YaRSS2 in the Preferences
  sidebar. Non-modal — torrent list stays interactive.
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

- **Deluge 2.x** (tested with 2.2.0 on Ubuntu 24.04 with Python 3.12, and
  2.2.1-dev on Ubuntu 25.10 with Python 3.14)
- **Python 3.6+** on the Deluge daemon. The egg must be built against the same
  Python version your Deluge daemon runs (see
  [Picking the right egg](#picking-the-right-egg) below).

YaRSS2 v2.x does **not** support Deluge 1.3.x.

## Picking the right egg

YaRSS2 ships pre-built eggs for multiple Python versions in each GitHub
[release](https://github.com/TSA3000/deluge-yarss2-webui/releases). The
filename suffix tells you which Python it's built for:

```
YaRSS2-2.2.5-py3.10.egg   ← for Deluge daemons running Python 3.10
YaRSS2-2.2.5-py3.11.egg   ← for Python 3.11
YaRSS2-2.2.5-py3.12.egg   ← for Python 3.12 (Ubuntu 24.04 default)
YaRSS2-2.2.5-py3.13.egg   ← for Python 3.13
YaRSS2-2.2.5-py3.14.egg   ← for Python 3.14 (Ubuntu 25.10 default)
```

**Deluge will silently fail to load an egg with the wrong Python suffix** —
the plugin won't appear in Preferences → Plug-ins, with no obvious error
message. So you need to know which Python your Deluge daemon actually runs.

### Linux — find your daemon's Python version

The system `python3` and the Python that Deluge runs under are sometimes
different (especially after distro upgrades). Check the running daemon
directly:

```bash
# Method 1 — read the libpython actually loaded by the running daemon
sudo cat /proc/$(pgrep -x deluged)/maps | grep -oE 'libpython[0-9]+\.[0-9]+' | sort -u
# Output example: libpython3.14 → grab YaRSS2-2.2.5-py3.14.egg
```

```bash
# Method 2 — check the deluged shebang
head -1 /usr/bin/deluged
# If it prints "#!/usr/bin/python3", check what python3 is symlinked to:
ls -l /usr/bin/python3
```

```bash
# Method 3 — check what cpython modules deluged has loaded
sudo lsof -p $(pgrep -x deluged) 2>/dev/null | grep -oE 'cpython-[0-9]+' | sort -u
# Output example: cpython-314 → Python 3.14
```

Once you know the version, download the matching egg from the GitHub release
page.

### Windows

Deluge for Windows ships with its own bundled Python interpreter. The
version depends on which Deluge installer you used:

| Deluge version | Bundled Python |
|----------------|----------------|
| Deluge 2.0.x   | Python 3.7     |
| Deluge 2.1.x   | Python 3.8 or 3.9 |
| Deluge 2.2.0   | Python 3.11    |

If unsure, check `Help → About` in the Deluge GTK client — it shows the
Python version. Or look at the bundled Python in the install directory:

```powershell
# Default install path
dir "C:\Program Files\Deluge\python*.dll"
```

The plugin folder on Windows is:

```
%APPDATA%\deluge\plugins\
```

## Installing

### Option A: use a prebuilt egg (recommended)

After identifying the right Python version per
[Picking the right egg](#picking-the-right-egg) above:

```bash
# Linux — adjust path/filename for your Deluge user and Python version
sudo cp YaRSS2-2.2.5-py3.14.egg /var/lib/deluge/.config/deluge/plugins/
sudo chown deluge:deluge /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.5-py3.14.egg
sudo chmod 644 /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.5-py3.14.egg
sudo systemctl restart deluged deluge-web
```

On Windows, drop the egg into `%APPDATA%\deluge\plugins\` and restart
Deluge.

### Option B: build from source

If a prebuilt egg for your Python version isn't published, build one
locally. You need that exact Python version installed:

```bash
# Linux — example for Python 3.12
git clone https://github.com/TSA3000/deluge-yarss2-webui.git
cd deluge-yarss2-webui
python3.12 setup.py bdist_egg
# Resulting egg in ./dist/YaRSS2-2.2.5-py3.12.egg
```

```powershell
# Windows — uses the `py` launcher to pick the right Python
git clone https://github.com/TSA3000/deluge-yarss2-webui.git
cd deluge-yarss2-webui
py -3.11 setup.py bdist_egg
# Resulting egg in .\dist\YaRSS2-2.2.5-py3.11.egg
```

Then copy the egg to your Deluge plugins directory as in Option A.

### Enable in Deluge

1. Open Deluge (GTK client) or Deluge WebUI.
2. **Preferences → Plugins** (GTK) or **Preferences → Plug-ins** (WebUI).
3. Tick **YaRSS2**. A new **YaRSS2** entry appears in the Preferences sidebar
   and a **YaRSS2** button appears in the main toolbar (WebUI).

## Quick start (WebUI)

1. Click the new **YaRSS2** button in the Deluge main toolbar (or
   **Preferences → YaRSS2** in the sidebar — both open the same window).
2. **RSS Feeds tab** → click **Add**. Fill in Name, URL, keep Update interval
   at 30 minutes, keep "Verify TLS certificate" ticked. Save.
3. **Subscriptions tab** → click **Add**. Pick your feed. Give it a name,
   enter a regex in "Regex include", e.g. `^Show Name S\d+E\d+ 1080p`.
   Optionally set "Move completed to". Save.
4. **RSS Feeds tab** → select your feed → click **Run now** to trigger an
   immediate fetch. Check your Deluge main view — matching torrents should
   appear.

New to regex? See [**REGEX-TUTORIAL.md**](./REGEX-TUTORIAL.md) for a
comprehensive guide from the basics through to production-quality filter
patterns.

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

These settings round-trip correctly when editing through the WebUI — they're
preserved from whatever values the GTK client set.

## Troubleshooting

### Plugin doesn't load

Most common cause: **Python version mismatch on the egg filename**. Deluge
will silently refuse to load an egg whose `pyX.YY` suffix doesn't match
its own Python version. There's no log error — it just doesn't appear in
the Plug-ins list.

**Step 1 — confirm your daemon's Python version:**

```bash
# What Python is the running daemon actually using?
sudo cat /proc/$(pgrep -x deluged)/maps | grep -oE 'libpython[0-9]+\.[0-9]+' | sort -u
# Example output: libpython3.14
```

**Step 2 — check what egg you have deployed:**

```bash
ls /var/lib/deluge/.config/deluge/plugins/ | grep -i yarss
# Example output: YaRSS2-2.2.5-py3.12.egg
```

If the daemon says `libpython3.14` but the egg says `py3.12`, that's your
problem. Download the matching egg from
[Releases](https://github.com/TSA3000/deluge-yarss2-webui/releases),
remove the old one, deploy the new one:

```bash
sudo systemctl stop deluged deluge-web
sudo rm /var/lib/deluge/.config/deluge/plugins/YaRSS2-*.egg
sudo cp YaRSS2-2.2.5-py3.14.egg /var/lib/deluge/.config/deluge/plugins/
sudo chown deluge:deluge /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.5-py3.14.egg
sudo chmod 644 /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.5-py3.14.egg
sudo systemctl start deluged deluge-web
```

**Step 3 — check the daemon log for import errors:**

```bash
sudo grep -iE 'yarss2|plugin' /var/log/deluge/deluged.log | tail -20
```

A successful load shows `Enabled YaRSS2 X.Y.Z` near the end. If you see
import-error tracebacks, paste them into a GitHub Issue.

### Plugin enabled but doesn't appear in WebUI

The daemon and `deluge-web` are separate processes that must both be
restarted after deploying a new egg:

```bash
sudo systemctl restart deluged deluge-web
```

Then in the browser:

```
F12 → Network tab → tick "Disable cache" → Ctrl+Shift+R (hard refresh)
```

Even with that, sometimes `deluge-web` hangs onto a cached plugin list.
Close all browser tabs pointing at the WebUI and open a fresh
incognito/private window.

### "Run now" says "not modified" and does nothing

Fixed in v2.2.0 — user-triggered runs bypass the ETag cache. If you see
this behavior on v2.2.x, the deployed egg may be older than v2.2.0.
Verify with:

```bash
unzip -p /var/lib/deluge/.config/deluge/plugins/YaRSS2-*.egg EGG-INFO/PKG-INFO | grep -i version
```

If it prints anything older than `Version: 2.2.0`, redeploy the latest.

### Nothing downloads even though matches happen

Verify the `move_completed` path exists and is writable by the Deluge user:

```bash
sudo -u deluge test -w /your/move/completed/path && echo OK || echo MISSING
```

Create it if missing. Deluge rejects adds with nonexistent move paths.

### Feed save "loses" the selected feed in a subscription

Fixed in v2.2.0. If you still see this, you're on a cached JS build.
Hard-refresh the browser as above.

### Subscription matches the right items but never triggers downloads

Check the subscription's `ignore_timestamp` and `last_match` settings:

```bash
sudo -u deluge python3 -c "
import json
raw = open('/var/lib/deluge/.config/deluge/yarss2.conf').read()
body = json.loads(raw[raw.index('}')+1:])
for s in body.get('subscriptions', {}).values():
    print(s['name'], '|', 'ignore_timestamp:', s['ignore_timestamp'],
          '|', 'last_match:', repr(s['last_match']))
"
```

If `ignore_timestamp` is `False` and `last_match` is set to a recent
timestamp, items in the feed older than `last_match` will be skipped.
For the first run on a new subscription, tick **Ignore timestamps** in
the Subscription editor — then untick it after the first successful match
to resume normal "only grab genuinely new items" behavior.

See the relevant section of [REGEX-TUTORIAL.md](./REGEX-TUTORIAL.md) for
a deeper explanation of the `last_match` mechanic.

### YaRSS2 button missing from main toolbar

The button is added via Deluge's `deluge.toolbar.add()` API. On some
Deluge builds this API may not be available — in that case the plugin
falls back to the Preferences sidebar entry only, which still works.

If you're sure your Deluge supports it but the button doesn't appear:
hard-refresh the browser, then check the JavaScript console (F12 →
Console) for any error mentioning `yarss2.js` or `deluge.toolbar`.

## Contributing

Pull requests welcome. The code style follows what was already in the tree:
Python 3, PEP 8-ish, 4-space indentation. The WebUI is ExtJS 3 (that's what
Deluge's WebUI uses) in a single file: `yarss2/data/yarss2.js`.

Tests live in `yarss2/tests/`. The regression tests added for v2.2.0 are in
`test_v9_fixes.py`.

## License

GPLv3 — see [`LICENSE`](./LICENSE).