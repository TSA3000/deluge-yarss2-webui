# YaRSS2 v2.2.3 — Release Notes

**Release date:** April 2026
**Maintainer:** Sam Mahdi
**Previous release:** v2.2.2 (regex live-preview)
**License:** GPLv3

Another additive WebUI polish release, adding **path autocomplete** to the
Subscription editor's Download location and Move completed fields.

## What's new

### Path autocomplete

When editing a subscription, the **Download location** and **Move
completed to** fields now suggest existing directories on the daemon's
filesystem as you type. This matches the behavior you'd get in the GTK
client.

**How it works:**

1. Start typing a path in either field, e.g. `/media/hdd3/`
2. After a brief debounce (250 ms), a dropdown appears listing
   subdirectories of whatever complete path prefix you've typed
3. Continue typing to narrow — e.g. `/media/hdd3/ct` filters to
   directories starting with `ct`
4. Arrow keys navigate, Enter/Tab select, Escape dismisses

**Under the hood:**

- Reuses the existing `get_completion_paths` @export method on Core,
  which was already in the codebase for the GTK client's autocomplete
- No new backend endpoints; pure frontend feature
- Debounced 250 ms between keystrokes to avoid filesystem spam
- Free typing remains fully allowed (`forceSelection: false`) — type
  paths that don't exist yet (directories that will be created on first
  download) without the UI rejecting them
- Hidden files/directories (names starting with `.`) are excluded from
  suggestions
- Dropdown width is 420 px so long paths don't get truncated

**Implementation:**

New reusable class `Deluge.ux.yarss2.PathComboField`, registered as
xtype `yarss2-pathcombo`. If future tabs need path autocomplete (feed
URLs → no; cookie values → no; so probably none), they can reuse this
drop-in.

## Upgrading from v2.2.2

```bash
sudo systemctl stop deluged
sudo rm /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.2-py3.12.egg
sudo cp YaRSS2-2.2.3-py3.12.egg /var/lib/deluge/.config/deluge/plugins/
sudo chown deluge:deluge /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.3-py3.12.egg
sudo chmod 644 /var/lib/deluge/.config/deluge/plugins/YaRSS2-2.2.3-py3.12.egg
sudo systemctl start deluged deluge-web
```

Hard-refresh browser (F12 → Network → Disable cache → Ctrl+Shift+R) to
pick up the new `yarss2.js`. Open any subscription, expand the Torrent
options fieldset, click into Download location — start typing and
suggestions appear.

No config migration. No schema change. No Python code change — only
`yarss2/data/yarss2.js` differs from v2.2.2.

## Known limitations (unchanged from v2.2.2)

Still not in the WebUI, still configurable via the GTK client:

- Email message templates editor (largest remaining piece)
- Tri-state torrent options UI (`Ask Deluge default` / `Force true` /
  `Force false` for `add_torrents_in_paused_state`, `auto_managed`,
  `sequential_download`, `prioritize_first_last_pieces`)

## Acknowledgments

Same as prior v2.2.x releases:

- **Camillo Dell'mour** — original YaRSS (2009)
- **bendikro** — YaRSS2 v1.x–v2.1.x (2012–2021)

---

For the complete commit-level changelog see [`CHANGELOG.md`](./CHANGELOG.md).
For install and usage documentation see [`README.md`](./README.md).
