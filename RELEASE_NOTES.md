# YaRSS2 v2.2.5 — Release Notes

**Release date:** April 28, 2026
**Maintainer:** Sam Mahdi
**Previous release:** v2.2.4 (path autocomplete, regex preview, Log tab, full WebUI port)
**License:** GPLv3

A UX-focused release that lifts YaRSS2 out of the cramped Preferences pane
and into its own floating window — accessible from a new toolbar button or
automatically when you click YaRSS2 in the Preferences sidebar. Also ships
a custom Deluge/RSS combined icon to give the plugin its own visual
identity.

## What's new

### Floating window

YaRSS2 used to live as a tab inside Deluge's modal Preferences dialog.
That worked, but the right pane got cramped once the regex preview,
path autocomplete, and Log tab were added — and the modal Preferences
dialog blocks interaction with the rest of Deluge while it's open.

v2.2.5 adds a floating window that opens YaRSS2 in a free-standing,
resizable, draggable container:

- **Resizable** — drag the corner to fit your screen
- **Draggable** — drag the title bar; constrained so it can't be dragged
  off-screen
- **Maximizable** — square button in the title bar to fill the viewport
- **Non-modal** — torrent list stays interactive while open
- **Singleton** — clicking the toolbar button or sidebar entry while the
  window is open brings it to the front instead of duplicating
- **Default size 1000×700** — gives the regex preview and Log tab room
  to breathe; min size 700×500
- **Closing hides, doesn't destroy** — state is preserved between opens
  (Log tab keeps its scroll position, Subscription dialogs remember
  their last selection, etc.)

The five tabs are unchanged from prior releases:
- RSS Feeds (grid + Add / Edit / Delete / Run now)
- Subscriptions (grid + edit dialog with regex preview + path autocomplete)
- Cookies (grid + name/value editor)
- General (max_concurrent_feeds, show_log_in_gui)
- Log (live tail of YaRSS2 log records)

### Two ways to open the window

**1. Toolbar button** — a new **YaRSS2** button is added to Deluge's
main top toolbar (inserted just before the Preferences button so it's
visible even on narrow viewports). Click it to open or focus the window.

**2. Preferences sidebar** — clicking **Preferences → YaRSS2** still
works; instead of trying to fit the whole plugin into the sidebar pane,
it now auto-opens the floating window and shows a placeholder message
in the right pane explaining where the UI went. An explicit
"Open YaRSS2" button is also there for the case when you've closed the
window and want to reopen it without leaving the Preferences dialog.

### New Deluge/RSS combined icon

A custom icon designed for this plugin specifically:

- Orange RSS-brand rounded square (`#ee802f`)
- White Deluge water-drop silhouette filling most of the square
- Orange RSS arcs and dot inside the drop, with the dot at the proper
  geometric origin shared with both arcs (the recognizable RSS triad)

The icon appears on:
- The toolbar button (16×16)
- The "Open YaRSS2" placeholder button in Preferences
- The floating window's title bar

It's embedded as an inline SVG data URI in `yarss2.js`, so no extra
image files ship inside the egg — the icon scales perfectly without
any HTTP requests or asset path resolution.

### Internal refactor

The five-tab construction was extracted into a shared factory
(`Deluge.ux.yarss2.buildTabPanel`) so the Preferences placeholder page
and the Window both initialize identical UIs. Future feature additions
land in both surfaces without code duplication.

A shared reload helper (`Deluge.ux.yarss2.reloadAllTabs`) does the same
for the config-fetch-and-broadcast logic.

## Upgrading from v2.2.4

```bash
sudo systemctl stop deluged deluge-web
sudo rm /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.4-py*.egg
sudo cp YaRSS2-2.2.5-pyX.YY.egg /var/lib/deluge/.config/deluge/plugins/
sudo chown deluge:deluge /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.5-pyX.YY.egg
sudo chmod 644 /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.5-pyX.YY.egg
sudo systemctl start deluged deluge-web
```

(replace `pyX.YY` with the Python version your daemon runs — typically
`py3.12` on Ubuntu 24.04 or `py3.14` on Ubuntu 25.10+).

Hard-refresh your browser (F12 → Network → "Disable cache" →
Ctrl+Shift+R) to pick up the new `yarss2.js`. Look for the new YaRSS2
button on the main toolbar with the orange icon.

No config migration. No schema change. Python code is unchanged from
v2.2.4 — only `yarss2/data/yarss2.js` is different.

## Known limitations

Unchanged from v2.2.4:

- Email message templates editor (still GTK-only)
- Tri-state torrent options UI (`Ask Deluge default` / `Force true` /
  `Force false` for `add_torrents_in_paused_state`, `auto_managed`,
  `sequential_download`, `prioritize_first_last_pieces`) — still GTK-only

## Acknowledgments

Same as prior v2.2.x releases:

- **Camillo Dell'mour** — original YaRSS (2009)
- **bendikro** — YaRSS2 v1.x–v2.1.x (2012–2021)

---

For the complete commit-level changelog see [`CHANGELOG.md`](./CHANGELOG.md).
For install and usage documentation see [`README.md`](./README.md).
For a regex tutorial covering subscription filter patterns, see
[`REGEX-TUTORIAL.md`](./REGEX-TUTORIAL.md).