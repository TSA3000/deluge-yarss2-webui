# YaRSS2 v2.2.1 — Release Notes

**Release date:** April 2026
**Maintainer:** Sam Mahdi
**Previous release:** v2.2.0 (same day; see [CHANGELOG.md](./CHANGELOG.md) for full v2.2.0 notes)
**License:** GPLv3

A small, additive release that completes the WebUI feature parity push from
v2.2.0 by adding a **Log tab** to the preferences page.

## What's new

### Log tab in the WebUI

The WebUI preferences page now has a fifth tab — **Log** — that live-tails
YaRSS2's log messages. It shows the same records you'd see in
`/var/log/deluge/deluged.log` filtered to the `yarss2` namespace, but inside
the browser.

Features:

- **Polls every 3 seconds** for new entries (incremental, so no re-fetching
  the whole buffer)
- **Level filter** — `All levels` / `INFO and above` / `WARNING and above` /
  `ERROR only`
- **Pause / Resume** — stops the poll loop when you want to read without the
  view shifting
- **Clear** — empties the in-memory buffer (does **not** touch the daemon's
  log file on disk)
- **Auto-scroll** toggle — follows new lines, or freezes so you can scroll
  back through history
- **Color-coded levels** — yellow for WARNING, red for ERROR/CRITICAL,
  gray for DEBUG, default for INFO
- **Bounded** — server keeps the last 1000 records; client keeps the last
  2000. Old entries fall off the front.

### Implementation

- New module `yarss2/util/log_buffer.py` with a thread-safe
  `LogBufferHandler` (subclass of `logging.Handler`, 1000-record bounded
  `collections.deque`, monotonic IDs for cursor-style polling).
- Attached to the top-level `yarss2` logger namespace on plugin enable,
  so records from every submodule (`yarss2.core`,
  `yarss2.rssfeed_handling`, `yarss2.torrent_handling`, etc.) are captured
  automatically without modifying any call sites.
- Detached cleanly on plugin disable so repeated enable/disable cycles
  don't stack handlers.
- Two new `@export` endpoints on `Core`:
  - `get_log_messages(since_id=0, max_messages=500)` — returns
    `{items, next_id, capacity}` where `items` is a list of
    `{id, time, level, logger, message}` dicts and `next_id` is the value
    the client should pass as `since_id` on its next poll.
  - `clear_log_messages()` — empties the buffer.
- Frontend is a new `Deluge.ux.yarss2.LogPanel` class in `yarss2/data/yarss2.js`,
  added as the fifth tab in the `YaRSS2Page` tab panel.

## Relationship to v2.2.0

This is purely additive — no existing behavior changed. Everything that
worked in v2.2.0 continues to work the same way. If you're already on
v2.2.0, upgrading is a drop-in egg swap.

v2.2.0 was the big release: security fixes, correctness fixes, the full
WebUI port (Feeds / Subscriptions / Cookies / General tabs), ETag caching,
configurable concurrency, and config schema v9. See the
[v2.2.0 release notes](https://github.com/TSA3000/deluge-yarss2-webui/releases/tag/v2.2.0)
or `CHANGELOG.md` for the complete list.

## Upgrading from v2.2.0

```bash
sudo systemctl stop deluged
sudo rm /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.0-py3.12.egg
sudo cp YaRSS2-2.2.1-py3.12.egg /var/lib/deluge/.config/deluge/plugins/
sudo chown deluge:deluge /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.1-py3.12.egg
sudo chmod 644 /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.1-py3.12.egg
sudo systemctl start deluged deluge-web
```

Hard-refresh your browser (F12 → Network → tick "Disable cache" →
Ctrl+Shift+R) so it picks up the new `yarss2.js`. Open
**Preferences → YaRSS2** — you should see the new **Log** tab. Click it and
within 3 seconds you'll see recent YaRSS2 activity streaming in.

No config migration. No schema bump. No new fields in `yarss2.conf`.

## Upgrading from v2.1.x

Same path as v2.2.0 — config auto-migrates from v8 → v9 on first load. See
the [v2.2.0 release notes](https://github.com/TSA3000/deluge-yarss2-webui/releases/tag/v2.2.0)
for details on the v8 → v9 migration and the new `verify_tls` /
`max_concurrent_feeds` options.

## Known limitations (unchanged from v2.2.0)

Still not in the WebUI, still configurable via the GTK client:

- Email message templates editor
- Tri-state torrent options UI (`Ask Deluge default` / `Force true` /
  `Force false` for `add_torrents_in_paused_state`, `auto_managed`,
  `sequential_download`, `prioritize_first_last_pieces`)
- Path autocomplete in Download location / Move completed fields
- Regex live-preview in subscription editor

## Acknowledgments

Same as v2.2.0:

- **Camillo Dell'mour** — original YaRSS (2009)
- **bendikro** — YaRSS2 v1.x–v2.1.x (2012–2021)

---

For the complete commit-level changelog see [`CHANGELOG.md`](./CHANGELOG.md).
For install and usage documentation see [`README.md`](./README.md).
