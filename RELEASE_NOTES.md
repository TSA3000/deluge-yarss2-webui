# YaRSS2 v2.2.4 — Release Notes

**Release date:** April 2026
**Maintainer:** Sam Mahdi
**Previous release:** v2.2.3 (path autocomplete)
**License:** GPLv3

A UX-focused release that lifts YaRSS2 out of the Preferences dialog and
into its own floating, resizable window — accessible from a new toolbar
button.

## What's new

### Floating YaRSS2 window

YaRSS2 used to live inside Deluge's modal Preferences dialog. To use it
you had to:

1. Open Preferences (modal — blocks the rest of the UI)
2. Click YaRSS2 in the sidebar
3. Work in a small pane
4. Close Preferences when done

That worked but had two pain points: the Preferences pane is narrow
(especially with the new Log tab and regex preview added), and you
couldn't see your torrent list while configuring subscriptions.

v2.2.4 adds a **YaRSS2** button to Deluge's main toolbar that opens the
plugin in a free-standing window:

- **Resizable** — drag the corner to make it as big as your screen
- **Draggable** — drag the title bar to move; constrained so it can't
  be dragged off-screen
- **Maximizable** — square button in the title bar to fill the viewport
- **Non-modal** — the rest of Deluge's UI stays interactive
- **Singleton** — clicking the toolbar button while the window is open
  brings it to the front instead of duplicating
- **Default size 1000x700** — gives the regex preview and Log tab room
  to breathe; min size 700x500
- **Closing hides, doesn't destroy** — state is preserved between opens
  so the Log tab keeps its scroll position, etc.

The five tabs are identical to before:
- RSS Feeds (grid + Add/Edit/Delete/Run now)
- Subscriptions (grid + edit window with regex preview + path autocomplete)
- Cookies (grid + name/value editor)
- General (max_concurrent_feeds, show_log_in_gui)
- Log (live tail of YaRSS2 log records)

### Backwards compatibility

The old **Preferences -> YaRSS2** entry is preserved. Existing users with
that muscle memory don't need to change anything. Both routes render the
same UI from the same code paths.

### Under the hood

The tab panel construction was refactored into a shared factory
(`Deluge.ux.yarss2.buildTabPanel`) that's consumed by both the
Preferences page and the window. Future tab additions or features will
appear in both surfaces automatically without code duplication.

The toolbar button is registered in `onEnable` and removed in
`onDisable`. If Deluge ever changes its toolbar API, the button is added
inside a try/catch — the plugin still works (via Preferences) even if
the button registration fails.

## Upgrading from v2.2.3

```bash
sudo systemctl stop deluged deluge-web
sudo rm /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.3-py3.12.egg
sudo cp YaRSS2-2.2.4-py3.12.egg /var/lib/deluge/.config/deluge/plugins/
sudo chown deluge:deluge /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.4-py3.12.egg
sudo chmod 644 /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.4-py3.12.egg
sudo systemctl start deluged deluge-web
```

Hard-refresh browser (F12 -> Network -> Disable cache -> Ctrl+Shift+R) to
pick up the new yarss2.js. You should see a **YaRSS2** button in the
toolbar (next to Down, Preferences, Connection Manager). Click it to
open the floating window.

The Preferences -> YaRSS2 entry continues to work as before.

No config migration. No schema change. Python code is unchanged from
v2.2.3 — only `yarss2/data/yarss2.js` differs.

## Known limitations

Unchanged from v2.2.3:

- Email message templates editor (still GTK-only)
- Tri-state torrent options UI (still GTK-only)

## Acknowledgments

Same as prior v2.2.x releases:

- **Camillo Dell'mour** — original YaRSS (2009)
- **bendikro** — YaRSS2 v1.x-v2.1.x (2012-2021)

---

For the complete commit-level changelog see [`CHANGELOG.md`](./CHANGELOG.md).
For install and usage documentation see [`README.md`](./README.md).
