## Changelog ##

v2.2.0 — 2026-04-19 (maintainer: Sam Mahdi; security + correctness + WebUI)

Security

* TLS certificate verification now enabled on torrent downloads (bundled
  certifi CA). Previously `verify=False` was hard-coded in
  `torrent_handling.download_torrent_file`, leaving every .torrent fetch
  vulnerable to in-path substitution. A per-feed `verify_tls` option (default
  True) lets users opt out for self-signed private trackers.
* Cookie matching in `util.http.get_matching_cookies_dict` replaced the
  substring check (`url.find(site) != -1`) with proper hostname comparison.
  A cookie scoped to `example.com` no longer leaks to `notexample.com` or
  `example.com.evil.tld`.

Correctness

* Fixed email-notification scope bug in
  `torrent_handling.TorrentHandler.add_torrents`: the send loop used a
  variable leaked from a preceding inner loop, so emails after the first
  carried the wrong subscription data and torrent list. Renamed the inner
  loop variable; the outer loop now uses `email_key` consistently.
* `_parse_size` in `rssfeed_handling` now recognises B, KB/KiB, MB/MiB,
  GB/GiB, TB/TiB (previously only GB and MB). Case-insensitive, supports
  fractional values, supports both SI (decimal) and IEC (binary) units.
  Unit table pulled out to module scope so the regex isn't recompiled per
  call.
* Torrent downloads now raise on HTTP 4xx/5xx (previously a failed response
  was silently stored as a successful empty `filedump`). 30-second request
  timeout added.
* Fixed user-visible "Succesfully" → "Successfully" in the add-torrent log
  message.

Features

* WebUI configuration management. Replaced the former "managed through the
  GTK UI client" notice page with a real tabbed preferences page:
  - RSS Feeds tab with grid, Add/Edit/Delete and a "Run now" action. Edit
    dialog exposes every field including the new v2.2 `verify_tls` toggle.
  - Subscriptions tab with grid + Add/Edit/Delete. Edit dialog has feed
    picker, regex include/exclude with per-side case-insensitivity,
    ignore-timestamp, download location, Label (plugin) support, per-sub
    speed and connection caps. Fields not exposed in the form
    (email_notifications, tri-state torrent options, custom_text_lines)
    are preserved across edits rather than reset.
  - Cookies tab with grid + Add/Edit/Delete. Edit dialog uses an editable
    name/value pair grid.
  - General tab exposes `max_concurrent_feeds` and `show_log_in_gui`.
  Email message templates and the log panel remain GTK-only in this pass.
  All CRUD uses the existing `@export` methods on Core — no new backend
  endpoints were needed. Implementation is a single file
  (`yarss2/data/yarss2.js`), ExtJS 3, ~600 lines.
* ETag / If-Modified-Since caching. `rssfeed_handling.get_rssfeed_parsed`
  now sends cached validators from the feed config and writes back the
  fresh ones returned by the server. A 304 Not Modified response becomes a
  fast no-op that skips parsing and subscription matching.
* Parallel feed fetches. `RSSFeedScheduler` now reads
  `general.max_concurrent_feeds` from config (default 1, the previous
  hard-coded value) and passes it to `RSSFeedRunQueue`. Raise it if a slow
  feed is blocking others. The queue's attribute was also renamed from the
  non-PEP-8 `concurrentMax` to `concurrent_max`.

Config

* Bumped `LATEST_CONFIG_VERSION` to 9. New migration
  `update_config_to_version9` adds the fields above with safe defaults.
  Downgrading to 2.1.x is non-destructive: the old code ignores the new
  keys.

Tests

* New file `yarss2/tests/test_v9_fixes.py` covers all four fixes. Cookie
  domain matching and size parsing are regression tests; the email scope
  and ETag persistence cases use stubs to avoid needing a live Deluge.

Additional late fixes (iterative deployment feedback)

* WebUI plugin registration — pre-existing import bug in bendikro 2.1.5
  where `yarss2/__init__.py` imported a class named `YaRSS2` from
  `.webui`, but the class is actually named `WebUI`. Changed to
  `from .webui import WebUI as _pluginCls`. Also added a missing
  `load_libs()` call to match the GTK loader.
* WebUI JSON-RPC call adapter — Deluge's JS client uses
  `{success, failure, scope}` callbacks, not Promises. Added a Proxy-based
  thenable wrapper so the WebUI code can use `.then(ok, err)` chains
  without per-call-site rewrites.
* Grid lazy-render guards — ExtJS 3's TabPanel lazy-renders inactive tabs;
  calling `store.loadData()` on an unrendered grid crashes in
  `GridView.refresh()`. Deferred data loads via `single: true` listener on
  the `render` event.
* Form label rendering — removed `baseCls: 'x-plain'` from all FormPanel
  instances (it strips the body class that FormLayout depends on for
  label positioning), replaced with `border: false` + explicit
  `layout: 'form'` + `labelSeparator: ':'`. Added "Feed" and "Subscription"
  fieldsets around top-level fields so dialog widths align visually with
  inner fieldset fields.
* Combo stores the valueField, not the display name — in ExtJS 3,
  `form.getValues()` DOM-serializes form inputs, which on a ComboBox
  returns the displayField (visible input) rather than the valueField
  (hidden input). Added a `readForm()` helper that iterates fields and
  reads values via `field.getValue()` per-field. Also strips emptyText
  placeholder leakage.
* emptyText no longer persisted as real values — ExtJS 3's
  `applyEmptyText` writes the placeholder into the DOM input's value,
  so `getValues()` returned it as a real value for fields that were
  never focused. The `readForm()` helper now filters this out.
* Magnet add exception handling — `TorrentManager.add(magnet=...)` was
  called without try/except, so a duplicate-infohash error (or any other
  libtorrent exception) on one magnet would abort the entire add loop
  and silently drop every subsequent match. Now caught per-magnet.
* Run now forces fresh fetch — `initiate_rssfeed_update` now clears the
  `etag` and `last_modified` validators before queueing the update, so
  user-triggered fetches always receive HTTP 200 with the feed body
  instead of being short-circuited by 304 Not Modified.
* 304 handling log cleanup — scheduled polls that receive 304 no longer
  log a misleading "No items retrieved" warning; they silently skip the
  subscription.

v2.1.5 - 2021-03-21

* Fix #63: Fix error on python 3.9 due to bug in feedparser

v2.1.4 - 2019-10-23

* Fix #53: Fix bug introduced in v2.1.2 where showing the RSS feed results was
           broken in thin client mode.
* Fix #48: Reduce the minimum updating interval from 5 to 1 minute.

v2.1.3 - 2019-10-17

* Fix #43: Unable to add Cookie-information

v2.1.2 - 2019-10-17

* Fix #53: Download RSS feeds via the plugin core (on the server)

v2.1.1 - 2019-10-15

* Fix: Bug adding torrent links to deluge

v2.1.0 - 2019-10-09

* Add WebUI Preferences page to inform that the plugin must be managed through the GTK UI client

v2.0.0 - 2019-10-04

* Fix #54: Add support for Deluge 2.X
* Replaced [feedparser](https://github.com/kurtmckee/feedparser) with
  [atoma](https://github.com/NicolasLM/atoma) for parsing RSS feeds

Note: YaRSS2 v2.X does not support Deluge 1.3.X

v1.4.3 - 2015-11-14

* Fix #10: Option to make YaRSS2 fetch subscriptions on startup
* Fix #13: Moved sending test email from daemon instead of client
* Fix #14: Problem with the ISO formating of 'Last matched' timestamp
* Fix #15: python traceback when RSS feed has no items
* Fix #20: An exception was thrown by the RSS update handler

v1.4.2 - 2015-11-11

* Fixed #26: Labels don't stay after restart
* Fixed #27: "Add torrent" on right click menu in subscription dialog gives stacktrace

v1.4.1 - 2015-10-06

* Fixed #24: Adding a second feed/subscription deleted previous

v1.4.0 - 2015-09-29

* Implemented support for setting label when Label plugin is enabled
* Updated feedparser to 5.2.0
* Updated requests library to v2.7
* Change user agent used when fetching RSS feeds with requests library.
* Added option to ignore timestamps in RSS feeds.
* Added option to prefer magnet links over torrent links if both are available.

v1.3.3 - 2014-07-25

* Updated feedparser to 5.1.3
* Fix Libtorrent error when adding magnet links in Deluge 1.3.3

v1.3.2 - 2013-12-10

 + Features
    * Now handles RSS url's that have spaces
    * Added right click option to copy a cookie

 + Bug Fix
     * Fix log window causing crash of Deluge.

v1.3.1 - 2013-10-06

 * Fix incorrect handler in exclude regex textbox (Bart Nagel)
 * Included missing file for Windows. (gtk.keysyms)

v1.3.0 - 2013-09-27

* Added new path chooser to settings.
* If an error occurs when fetching RSS feeds it should no longer stop the
  scheduler from running.

v1.2.1 - 2013-01-12

* Fixed bug causing running subscriptions manually to fail.

v1.2.0 - 2012-12-10

 + Features
    * Added new options in the subscription dialog (Bandwidth, General).
    * Added support for the enclosure tag in RSS feeds.
    * Using the requests library to handle redirects properly so that non-direct
      torrent links work.
    * Added "Copy link to clipboard" button to the right click menu in the
      subscription panel.
    * When failing to download a torrent in the dialog subscription, the page
      content is now shown in a message pane at the bottom.
    * Removed GTK (client) dependency on libtorrent-python


 + Bug Fix:
    * Fixed bug crashing Deluge when adding torrents
    * The checkbox ("On torrent added") to enable a notification in the list of
      notifications
      for a subscription was not working.
    * Tooltips were displayed on the wrong row.

v1.1.3 - 2012-10-17

* Fixed bug that caused sending emails to fail.
* The 'From email address' field value in configurations was not loaded.
* Improved verification of the config on startup. (Fix errors)

v1.1.2 - 2012-10-05

* Fixed error where ComboBox.get_active_text would return None.
* The current value in "Move completed" and "Download location" was added twice.

v1.1.1 - 2012-10-03

* Fixed import error when running YaRSS2 on daemon without gtk installed.
* feedparser library was unable to parse some timestamps.
* The order of the torrents in the torrent list in the subscription dialog was incorrect.

v1.1.0 - 2012-09-12

* Added panel for log messages.
* Added functionality to reset the last matched timestamp for subscriptions. (Options tab in subscription dialog)
* Fixed bug where RSS feeds with no proper tag for the timestamp when the torrent was published would crash YaRSS2.
* Fixed bug where the 'Published' column in matching panel for subscriptions wasn't properly populated.
* Hopefully fixed bug in GUI that could result in Deluge crashing.

v1.0.4 - 2012-06-27

* Added support for magnet links.
* Running RSS feed fetches in separate thread to avoid having the deluge daemon being busy for too long.
* Added option "Obey TTL" in RSS Feed dialog. With this checked the "Update Interval" will be updated with the TTL value of the RSS Feed.
* Added option "Download location" in subscription dialog.
* Fixed bug where it was possible to delete an email message used by subscriptions for notifications.

v1.0.3 - 2012-05-17

* When adding a RSS Feed or changing the RSS Feed update interval the RSS Feed is now properly (re)schedules with the (new) update interval.
  (Previously a restart of deluge was required)
* After deleting a RSS Feed it is properly stopped from running.
* Added timeout for 10 seconds on feedparser so deluge won't hang in case the server doesn't respond properly.
* "Last update" field in RSS Feeds is now updated properly.
* Added "Last matched" field in Subscriptions list with the timestamp for when the subscription last matched a torrent.
* No longer allow deleting RSS Feeds with subscriptions registered.
* Fixed issue in feedparser where '&' in torrent URLs was converted to &amp.

v1.0.2 - 2012-04-07

* Added mime modules for sending email (required on Windows).

v1.0.1 - 2012-04-01

* Unicode characers can now be used to search.
* Added tests to test some of the most important functionality

v1.0 - 2012-03-27

* First release

(Tested with Deluge 1.3.5)
