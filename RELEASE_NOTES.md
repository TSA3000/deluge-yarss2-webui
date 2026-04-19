# YaRSS2 v2.2.0 — Release Notes

**Release date:** April 2026
**Maintainer:** Sam Mahdi
**Based on:** YaRSS2 v2.1.5 (bendikro, 2021)
**License:** GPLv3

This release is a consolidated security, correctness, and feature update for
the YaRSS2 Deluge plugin, with the primary goal of bringing first-class WebUI
support to the plugin. All changes preserve backwards compatibility with
existing configs and existing GTK client workflows.

## Why this release

YaRSS2 has been stable at v2.1.5 since 2021. Over time three issues
accumulated:

1. **A latent TLS security issue** — `verify=False` hardcoded on `.torrent`
   file fetches, making every download vulnerable to path substitution.
2. **WebUI users were second-class citizens** — the plugin's WebUI page just
   said "use the GTK client." That's unworkable for headless servers.
3. **Subtle correctness bugs** — cookie domain matching, email scope, size
   parsing, and concurrency limits.

This release fixes all three.

## What's fixed

### Security

- **TLS verification restored** on all HTTP-based torrent file downloads.
  Previously `torrent_handling.download_torrent_file()` passed `verify=False`
  to requests, disabling certificate validation entirely. Now uses the
  bundled `certifi` CA bundle by default. Users who need to work with
  self-signed private trackers can disable verification per-feed via the new
  `verify_tls` option (default: `True`).
- **Cookie hostname matching** in `util.http.get_matching_cookies_dict()`
  replaced a substring check (`url.find(site) != -1`) with proper
  hostname-boundary comparison. Before this fix, a cookie scoped to
  `tracker.example.com` could leak to URLs like `tracker.example.com.evil.tld`
  or `nottracker.example.com`.
- **HTTP 4xx/5xx now raises.** Previously, a failed HTTP response was stored
  silently as a successful empty `filedump`, leading to confusing "added empty
  torrent" behaviors.
- A **30-second timeout** is now enforced on torrent file requests.

### Correctness

- **Email notification scope bug** in
  `torrent_handling.TorrentHandler.add_torrents` — the outer send loop was
  inadvertently using a variable (`key`) that leaked from a preceding inner
  loop, so multi-notification configs sent the wrong subscription data and
  torrent list for all emails after the first. Renamed the inner loop's
  variable to `notif_key`.
- **Size parser** `_parse_size` in `rssfeed_handling` now correctly handles
  `B`, `KB`/`KiB`, `MB`/`MiB`, `GB`/`GiB`, and `TB`/`TiB`. Previously only
  `GB` and `MB` were recognized. Case-insensitive, supports fractional
  values, handles both SI (decimal) and IEC (binary) units. Table is
  module-scoped so the regex isn't recompiled per call.
- **Duplicate-infohash resilience.** Previously, an `AddTorrentError` from
  libtorrent on one magnet (commonly caused by the same infohash already
  being in Deluge's session) would propagate up and abort the entire add
  loop, causing every subsequent magnet in the same batch to be silently
  dropped. Now caught per-torrent and logged as a warning.
- **Typo fix**: `Succesfully` → `Successfully` in the add-torrent log
  message.

### Features

- **Complete WebUI port** — new tabbed preferences panel that replaces the
  old 67-line "managed through the GTK UI client" notice. Implemented as
  a single ExtJS 3 file (`yarss2/data/yarss2.js`, ~870 lines).
  - **RSS Feeds tab** — grid with Add / Edit / Delete / Run now.
  - **Subscriptions tab** — grid with Add / Edit / Delete.
  - **Cookies tab** — grid with Add / Edit / Delete, plus an editable
    name/value pair grid for each cookie.
  - **General tab** — exposes `max_concurrent_feeds` and `show_log_in_gui`.
  - All CRUD routes through the existing `@export` methods on Core. No new
    backend endpoints were needed.
  - Fields not exposed in the WebUI forms (email_notifications, tri-state
    torrent options, custom_text_lines) are preserved across edits rather
    than reset — the WebUI and GTK client can coexist without stepping on
    each other.
- **ETag / If-Modified-Since caching** in `rssfeed_handling`. The handler
  now sends cached validators with each fetch and writes back the fresh
  ones returned by the server. A 304 response becomes a fast no-op that
  skips re-parsing. **"Run now" explicitly bypasses this cache** so
  user-triggered fetches always pull fresh data.
- **Configurable parallel feed fetches.** `RSSFeedScheduler` reads
  `general.max_concurrent_feeds` from config (default: 1, preserving
  previous behavior) and passes it to `RSSFeedRunQueue`. Raise it if a
  slow feed is blocking faster ones. The queue attribute was also
  renamed from the non-PEP-8 `concurrentMax` to `concurrent_max`.
- **New `verify_tls` per-feed toggle** — ticked by default. Lets you opt
  out of TLS verification for individual feeds (e.g. self-signed private
  trackers). Exposed in both the WebUI and the underlying config.

### Config

- Schema bumped to **version 9**. New migration `update_config_to_version9`
  adds the fields above with safe defaults. Runs idempotently and is safe
  to re-run. Downgrading to v2.1.x remains non-destructive — the old code
  ignores the new keys.

### Tests

- New file `yarss2/tests/test_v9_fixes.py` covers all the fixes. Cookie
  domain matching and size parsing are straightforward regression tests;
  the email scope and ETag persistence cases use stubs to avoid needing
  a live Deluge instance.

## WebUI implementation notes

A few ExtJS-3 specific traps were hit and fixed during the WebUI port. These
are documented for anyone extending the WebUI later:

- **Deluge's JSON-RPC client uses `{success, failure, scope}` callbacks,
  not Promises.** The WebUI wraps every call in a minimal thenable via a
  `Proxy`, so call sites can use idiomatic `.then(ok, err)` chains without
  12 call-site rewrites if Deluge's client ever changes.
- **Grid data load must be deferred until tab render.** ExtJS 3 lazy-renders
  inactive `TabPanel` children; calling `store.loadData()` on an unrendered
  grid crashes `GridView.refresh()` with a `stopEditing` undefined error.
  Fixed by deferring `loadData()` via a `single: true` listener on `render`.
- **`baseCls: 'x-plain'`** strips the body class that FormPanel's form
  layout uses to position labels. This causes labels to render outside
  the dialog's visible area after the first hide/show cycle. Use
  `border: false` instead.
- **`form.getValues()` reads form DOM inputs directly**, which means:
  (a) for a ComboBox with `valueField`/`displayField`, it returns the
  *display* name (which is on the visible `<input name="...">`), not the
  value; (b) for a TextField with `emptyText`, it returns the placeholder
  string when the field was never focused (ExtJS 3's `applyEmptyText`
  writes the placeholder to the DOM input). Both issues are avoided by
  iterating fields and calling `field.getValue()` per-field. See the
  `readForm` helper in `yarss2.js`.

## Upgrading from v2.1.x

No user action required. First daemon start with v2.2.0 migrates the config
from v8 → v9 automatically. Original config is preserved in-place; only new
fields are added.

If you have feeds that previously relied on TLS verification being off
(which was never a documented setting, but a hidden bug), you will see
certificate errors on them after upgrading. Edit each affected feed in the
WebUI and untick "Verify TLS certificate".

## Known limitations

The following are **not** in this release but remain available through the
GTK client:

- Email message templates editor (the `email_messages` config is preserved
  across WebUI edits but can't be edited from the WebUI)
- Log panel
- Tri-state torrent options UI (`Ask Deluge default` / `Force true` /
  `Force false` for `add_torrents_in_paused_state`, `auto_managed`,
  `sequential_download`, `prioritize_first_last_pieces`)
- Path autocomplete in Download location / Move completed fields
- Regex live-preview in subscription editor

Subscription fields that aren't displayed in the WebUI form are nonetheless
round-tripped correctly on save — they retain whatever values the GTK client
last wrote.

## Acknowledgments

Thanks to:

- **Camillo Dell'mour** for the original YaRSS implementation (2009).
- **bendikro** for a decade of YaRSS2 maintenance (2012–2021).

Both original copyright notices are preserved per the GPLv3 terms under
which YaRSS2 has always been distributed.

---

For the full commit-level changelog see [`CHANGELOG.md`](./CHANGELOG.md).
For install and usage documentation see [`README.md`](./README.md).
