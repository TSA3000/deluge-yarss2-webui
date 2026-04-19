/*
 * yarss2.js — WebUI for the YaRSS2 Deluge plugin.
 *
 * Copyright (C) 2026 YaRSS2 v2.2 contributors
 * Based on earlier work (C) 2019 bendikro <bro.devel+yarss2@gmail.com>
 *
 * Licensed under GPLv3. See LICENSE for details.
 *
 * Layout:
 *   - Preferences page with a tabbed panel (Feeds / Subscriptions /
 *     Cookies / General).
 *   - Each CRUD tab = a grid + Add/Edit/Delete buttons + a modal edit window.
 *   - Email messages and log panel are deliberately not ported in this pass;
 *     they remain manageable from the GTK client.
 *
 * All CRUD goes through existing @export methods on yarss2.Core:
 *   get_config, save_rssfeed, save_subscription, save_cookie,
 *   save_general_config, initiate_rssfeed_update.
 * No new backend methods were added.
 */

Ext.ns('Deluge.ux.yarss2');
Ext.ns('Deluge.ux.preferences');
Ext.ns('Deluge.plugins');

/* ------------------------------------------------------------------ *
 * Shared helpers
 * ------------------------------------------------------------------ */

// Deluge's JSON-RPC client uses {success, failure, scope} callbacks rather
// than Promises. We wrap every call in a minimal thenable so the rest of
// this file can use `.client().foo(args).then(ok, err)` idiomatically.
Deluge.ux.yarss2._thenable = function(invoke) {
    var d = { _okFn: null, _errFn: null, _ok: null, _err: null,
        then: function(okFn, errFn) {
            this._okFn = okFn; this._errFn = errFn;
            if (this._ok) okFn(this._ok.v);
            else if (this._err && errFn) errFn(this._err.v);
            return this;
        }
    };
    invoke(
        function(r) { if (d._okFn) d._okFn(r); else d._ok = { v: r }; },
        function(e) { if (d._errFn) d._errFn(e); else d._err = { v: e }; }
    );
    return d;
};

Deluge.ux.yarss2.client = function() {
    var real = deluge.client.yarss2;
    if (!real) {
        // Core plugin not yet registered — return a stub that errors cleanly.
        return new Proxy({}, { get: function() {
            return function() {
                return Deluge.ux.yarss2._thenable(function(_, fail) {
                    fail({ message: 'YaRSS2 core plugin not loaded' });
                });
            };
        } });
    }
    return new Proxy({}, {
        get: function(_, prop) {
            var fn = real[prop];
            if (typeof fn !== 'function') return undefined;
            return function() {
                var args = Array.prototype.slice.call(arguments);
                return Deluge.ux.yarss2._thenable(function(success, failure) {
                    args.push({ success: success, failure: failure });
                    fn.apply(real, args);
                });
            };
        }
    });
};

// Read a FormPanel's values by walking each field and calling getValue().
// Ext 3's form.getValues() reads DOM inputs directly, which (a) returns the
// display text of combos (not the valueField) because the name attr lives
// on the visible input, and (b) returns emptyText placeholder strings as
// actual values for text fields that were never focused. This bypasses both
// problems.
Deluge.ux.yarss2.readForm = function(formPanel) {
    var out = {};
    formPanel.getForm().items.each(function(f) {
        if (!f.isFormField) return;
        var name = f.getName();
        if (!name) return;
        var v = f.getValue();
        // Clear emptyText leakage (TextField.getValue returns DOM value, which
        // is the emptyText string when applyEmptyText has been called).
        if (f.emptyText && v === f.emptyText) v = '';
        out[name] = v;
    });
    return out;
};

Deluge.ux.yarss2.dictToRows = function(dict) {
    // Config uses dict-keyed records ({"0": {...}, "1": {...}}). ExtJS stores
    // want an array. Each record's own "key" is preserved.
    var rows = [];
    if (!dict) return rows;
    Ext.iterate(dict, function(k, v) {
        var copy = Ext.apply({}, v);
        if (copy.key === undefined) copy.key = k;
        rows.push(copy);
    });
    return rows;
};

Deluge.ux.yarss2.errorAlert = function(title, err) {
    var msg = (err && err.message) ? err.message : String(err);
    Ext.Msg.alert(title, Ext.util.Format.htmlEncode(msg));
};

Deluge.ux.yarss2.confirm = function(title, msg, onYes) {
    Ext.Msg.show({
        title: title,
        msg: msg,
        buttons: Ext.Msg.YESNO,
        icon: Ext.MessageBox.QUESTION,
        fn: function(btn) { if (btn === 'yes') onYes(); }
    });
};

/* ------------------------------------------------------------------ *
 * Path autocomplete field — behaves like a TextField (no visible
 * dropdown trigger) but calls yarss2.get_completion_paths on keyup
 * and shows matching directories as a dropdown. User can still free-
 * type paths that don't exist yet (forceSelection is false).
 * ------------------------------------------------------------------ */

Deluge.ux.yarss2.PathComboField = Ext.extend(Ext.form.ComboBox, {
    // Look-and-feel: make the combo resemble a regular textfield.
    hideTrigger: true,
    typeAhead: false,
    forceSelection: false,
    editable: true,
    // We manage queries manually, so local mode keeps ComboBox from
    // triggering its own load.
    mode: 'local',
    triggerAction: 'all',
    minChars: 1,
    // Dropdown dimensions.
    listWidth: 420,
    itemSelector: 'div.x-combo-list-item',
    displayField: 'path',
    valueField: 'path',
    // Delay between last keystroke and completion request (ms).
    completionDelay: 250,

    initComponent: function() {
        this.store = new Ext.data.JsonStore({
            fields: ['path'],
            data: []
        });
        Deluge.ux.yarss2.PathComboField.superclass.initComponent.call(this);
        this.on('keyup', this.onKeyUpForCompletion, this);
        this.on('beforedestroy', function() {
            if (this._completionTimer) clearTimeout(this._completionTimer);
        }, this);
    },

    // Swallow empty-string suggestions and skip keys that control the
    // dropdown itself (arrows, enter, tab, escape).
    onKeyUpForCompletion: function(field, e) {
        var k = e.getKey();
        if (k === e.UP || k === e.DOWN || k === e.ENTER ||
            k === e.TAB || k === e.ESC || k === e.LEFT || k === e.RIGHT) {
            return;
        }
        var self = this;
        if (this._completionTimer) clearTimeout(this._completionTimer);
        this._completionTimer = setTimeout(function() {
            self.fetchCompletions();
        }, this.completionDelay);
    },

    fetchCompletions: function() {
        var self = this;
        var value = this.getRawValue() || '';
        if (value.length < this.minChars) {
            this.collapse();
            return;
        }
        Deluge.ux.yarss2.client().get_completion_paths({
            completion_text: value,
            show_hidden_files: false
        }).then(
            function(result) {
                var paths = (result && result.paths) || [];
                // Deduplicate (already sorted server-side).
                var uniq = [];
                var seen = {};
                for (var i = 0; i < paths.length; i++) {
                    if (!seen[paths[i]]) { seen[paths[i]] = true; uniq.push(paths[i]); }
                }
                self.store.loadData(uniq.map(function(p) { return { path: p }; }));
                if (uniq.length > 0) {
                    self.expand();
                } else {
                    self.collapse();
                }
            },
            function(err) {
                // Don't spam the user during typing; just log.
                if (window.console) console.warn('Path completion failed:', err);
                self.collapse();
            }
        );
    }
});
// Register so xtype: 'yarss2-pathcombo' works.
Ext.reg('yarss2-pathcombo', Deluge.ux.yarss2.PathComboField);

/* ------------------------------------------------------------------ *
 * RSS Feed edit window
 * ------------------------------------------------------------------ */

Deluge.ux.yarss2.RssFeedWindow = Ext.extend(Ext.Window, {
    title: _('RSS Feed'),
    width: 560,
    height: 500,
    layout: 'fit',
    modal: true,
    plain: true,
    closeAction: 'hide',

    initComponent: function() {
        Deluge.ux.yarss2.RssFeedWindow.superclass.initComponent.call(this);

        this.form = new Ext.form.FormPanel({
            border: false,
            bodyStyle: 'padding: 10px',
            layout: 'form',
            labelWidth: 150,
            labelSeparator: ':',
            autoScroll: true,
            items: [{
                xtype: 'fieldset', title: _('Feed'), collapsible: false,
                defaults: { anchor: '100%' },
                items: [
                    { xtype: 'textfield', fieldLabel: _('Name'), name: 'name', allowBlank: false },
                    { xtype: 'textfield', fieldLabel: _('URL'),  name: 'url',  allowBlank: false },
                    { xtype: 'textfield', fieldLabel: _('Site'), name: 'site',
                        emptyText: _('e.g. tracker.example.com — used to scope cookies') },
                    { xtype: 'numberfield', fieldLabel: _('Update interval (min)'),
                        name: 'update_interval', minValue: 1, value: 120 },
                    { xtype: 'textfield', fieldLabel: _('User-Agent'), name: 'user_agent',
                        emptyText: _('Leave blank for default') },
                    { xtype: 'checkbox', fieldLabel: _('Active'), name: 'active', checked: true },
                    { xtype: 'checkbox', fieldLabel: _('Obey feed TTL'), name: 'obey_ttl' },
                    { xtype: 'checkbox', fieldLabel: _('Update on startup'), name: 'update_on_startup' },
                    { xtype: 'checkbox', fieldLabel: _('Prefer magnet links'), name: 'prefer_magnet' },
                    { xtype: 'checkbox', fieldLabel: _('Verify TLS certificate'),
                        name: 'verify_tls', checked: true,
                        boxLabel: _('Uncheck only for self-signed private trackers') }
                ]
            }]
        });
        this.add(this.form);

        this.saveBtn   = this.addButton({ text: _('Save'),   handler: this.onSave,   scope: this });
        this.cancelBtn = this.addButton({ text: _('Cancel'), handler: this.onCancel, scope: this });
    },

    showForRecord: function(record) {
        // record is null for "Add", or a feed dict for "Edit".
        this.editingRecord = record;
        this.setTitle(record ? _('Edit RSS Feed') : _('Add RSS Feed'));
        var defaults = {
            name: '', url: '', site: '', update_interval: 120,
            user_agent: '', active: true, obey_ttl: false,
            update_on_startup: false, prefer_magnet: false,
            verify_tls: true
        };
        var values = Ext.apply(defaults, record || {});
        this.form.getForm().setValues(values);
        this.show();
    },

    onSave: function() {
        var form = this.form.getForm();
        if (!form.isValid()) return;
        var values = Deluge.ux.yarss2.readForm(this.form);
        var data = {
            name: values.name,
            url: values.url,
            site: values.site || '',
            update_interval: parseInt(values.update_interval, 10) || 120,
            user_agent: values.user_agent || '',
            active: !!values.active,
            obey_ttl: !!values.obey_ttl,
            update_on_startup: !!values.update_on_startup,
            prefer_magnet: !!values.prefer_magnet,
            verify_tls: !!values.verify_tls,
            // Preserve server-managed fields if we're editing an existing row.
            last_update: (this.editingRecord && this.editingRecord.last_update) || '',
            etag: (this.editingRecord && this.editingRecord.etag) || '',
            last_modified: (this.editingRecord && this.editingRecord.last_modified) || ''
        };
        if (this.editingRecord && this.editingRecord.key !== undefined) {
            data.key = this.editingRecord.key;
        }
        var self = this;
        Deluge.ux.yarss2.client().save_rssfeed(data.key || null, data, false).then(
            function() { self.hide(); self.fireEvent('yarss2-saved'); },
            function(err) { Deluge.ux.yarss2.errorAlert(_('Failed to save feed'), err); }
        );
    },

    onCancel: function() { this.hide(); }
});

/* ------------------------------------------------------------------ *
 * Subscription edit window
 * ------------------------------------------------------------------ */

Deluge.ux.yarss2.SubscriptionWindow = Ext.extend(Ext.Window, {
    title: _('Subscription'),
    width: 720,
    height: 720,
    layout: 'fit',
    modal: true,
    plain: true,
    closeAction: 'hide',

    // Cached feed items for live preview. Reset on feed change.
    _previewItems: null,
    _previewFeedKey: null,
    _previewLoading: false,

    initComponent: function() {
        Deluge.ux.yarss2.SubscriptionWindow.superclass.initComponent.call(this);

        var self = this;
        this.feedStore = new Ext.data.JsonStore({
            fields: ['key', 'name'],
            data: []
        });

        this.form = new Ext.form.FormPanel({
            border: false,
            bodyStyle: 'padding: 10px',
            layout: 'form',
            labelWidth: 150,
            labelSeparator: ':',
            autoScroll: true,
            defaults: { anchor: '100%' },
            items: [
                {
                    xtype: 'fieldset', title: _('Subscription'), collapsible: false,
                    defaults: { anchor: '100%' },
                    items: [
                        { xtype: 'textfield', fieldLabel: _('Name'), name: 'name', allowBlank: false },
                        {
                            xtype: 'combo', fieldLabel: _('RSS Feed'), name: 'rssfeed_key',
                            store: this.feedStore, valueField: 'key', displayField: 'name',
                            mode: 'local', triggerAction: 'all', forceSelection: true,
                            editable: false, allowBlank: false,
                            listeners: {
                                select: function(cb, rec) {
                                    self.onFeedChanged(rec.get('key'));
                                }
                            }
                        },
                        { xtype: 'checkbox', fieldLabel: _('Active'), name: 'active', checked: true }
                    ]
                },
                {
                    xtype: 'fieldset', title: _('Filter'), collapsible: false,
                    defaults: { anchor: '100%' },
                    items: [
                        { xtype: 'textfield', fieldLabel: _('Regex include'),
                            name: 'regex_include',
                            emptyText: _('e.g. \\.S01E\\d+\\.1080p.*x265'),
                            enableKeyEvents: true,
                            listeners: { keyup: function() { self.updatePreview(); } } },
                        { xtype: 'checkbox', fieldLabel: _('Ignore case (include)'),
                            name: 'regex_include_ignorecase', checked: true,
                            listeners: { check: function() { self.updatePreview(); } } },
                        { xtype: 'textfield', fieldLabel: _('Regex exclude'),
                            name: 'regex_exclude',
                            enableKeyEvents: true,
                            listeners: { keyup: function() { self.updatePreview(); } } },
                        { xtype: 'checkbox', fieldLabel: _('Ignore case (exclude)'),
                            name: 'regex_exclude_ignorecase', checked: true,
                            listeners: { check: function() { self.updatePreview(); } } },
                        { xtype: 'checkbox', fieldLabel: _('Ignore timestamps'),
                            name: 'ignore_timestamp',
                            boxLabel: _('Match items even if published before last run') }
                    ]
                },
                {
                    xtype: 'fieldset', title: _('Live preview'), collapsible: true, collapsed: false,
                    defaults: { anchor: '100%' },
                    items: [
                        {
                            xtype: 'panel', border: false, bodyStyle: 'padding: 0 4px 6px 4px',
                            html: '<div class="yarss2-preview-status" style="font-size:11px;color:#888;margin-bottom:4px;">' +
                                  _('Select a feed above to see items. Matching items are green; excluded items are red.') +
                                  '</div>' +
                                  '<div class="yarss2-preview-list" style="height:200px;overflow:auto;' +
                                  'border:1px solid #444;padding:4px;font-family:Menlo,Consolas,monospace;' +
                                  'font-size:11px;line-height:1.4;white-space:nowrap;"></div>' +
                                  '<div style="font-size:10px;color:#888;margin-top:4px;">' +
                                  _('Preview uses JavaScript RegExp for speed. The daemon uses Python re, which is near-identical for common patterns.') +
                                  '</div>'
                        },
                        {
                            xtype: 'panel', border: false, bodyStyle: 'padding: 4px',
                            layout: 'hbox',
                            items: [
                                { xtype: 'button', text: _('Refresh feed'),
                                    handler: function() { self.fetchPreviewItems(true); } }
                            ]
                        }
                    ]
                },
                {
                    xtype: 'fieldset', title: _('Torrent options'), collapsible: true, collapsed: true,
                    defaults: { anchor: '100%' },
                    items: [
                        { xtype: 'yarss2-pathcombo', fieldLabel: _('Download location'),
                            name: 'download_location',
                            emptyText: _('Leave empty for Deluge default') },
                        { xtype: 'yarss2-pathcombo', fieldLabel: _('Move completed to'),
                            name: 'move_completed',
                            emptyText: _('Leave empty to disable move-on-complete') },
                        { xtype: 'textfield', fieldLabel: _('Label'), name: 'label',
                            emptyText: _('Requires the Label plugin') },
                        { xtype: 'numberfield', fieldLabel: _('Max download speed (KiB/s)'),
                            name: 'max_download_speed', value: -2,
                            emptyText: _('-2 = Deluge default, -1 = unlimited') },
                        { xtype: 'numberfield', fieldLabel: _('Max upload speed (KiB/s)'),
                            name: 'max_upload_speed', value: -2 },
                        { xtype: 'numberfield', fieldLabel: _('Max connections'),
                            name: 'max_connections', value: -2 },
                        { xtype: 'numberfield', fieldLabel: _('Max upload slots'),
                            name: 'max_upload_slots', value: -2 }
                    ]
                }
            ]
        });
        this.add(this.form);

        this.saveBtn   = this.addButton({ text: _('Save'),   handler: this.onSave,   scope: this });
        this.cancelBtn = this.addButton({ text: _('Cancel'), handler: this.onCancel, scope: this });
    },

    // DOM helpers for the preview block.
    getPreviewListEl: function() {
        var body = this.form && this.form.body ? this.form.body.dom : null;
        if (!body) return null;
        return body.querySelector('.yarss2-preview-list');
    },
    getPreviewStatusEl: function() {
        var body = this.form && this.form.body ? this.form.body.dom : null;
        if (!body) return null;
        return body.querySelector('.yarss2-preview-status');
    },

    // Called when the feed combo selection changes — invalidate cache
    // and fetch the new feed's items.
    onFeedChanged: function(feedKey) {
        this._previewFeedKey = feedKey;
        this._previewItems = null;
        this.fetchPreviewItems(false);
    },

    // Fetch the feed's current items via the backend. If `force` is true,
    // refetch even if we already have cached items for this feed.
    fetchPreviewItems: function(force) {
        var self = this;
        if (!this._previewFeedKey) return;
        if (this._previewLoading) return;
        if (!force && this._previewItems) { this.updatePreview(); return; }

        var feed = this._feedsByKey && this._feedsByKey[this._previewFeedKey];
        if (!feed) return;

        // Strip the cached ETag/Last-Modified validators so the daemon
        // re-fetches the feed body instead of returning 304 Not Modified
        // with no items. Preview needs the actual content.
        var feedCopy = Ext.apply({}, feed);
        feedCopy.etag = '';
        feedCopy.last_modified = '';

        var status = this.getPreviewStatusEl();
        if (status) status.innerHTML = _('Fetching feed items…');
        this._previewLoading = true;

        Deluge.ux.yarss2.client().get_rssfeed_parsed(feedCopy, null, feedCopy.user_agent || null).then(
            function(result) {
                self._previewLoading = false;
                if (!result) {
                    if (status) status.innerHTML = _('Failed to fetch feed.');
                    return;
                }
                if (result.not_modified) {
                    // 304 = the daemon's cache is stale for preview purposes;
                    // we'd need a cache-bypass. For now surface the state.
                    if (status) status.innerHTML = _('Feed returned 304 (not modified). Click "Refresh feed" to force a fresh fetch.');
                }
                // items is a dict of {key: {title, link, ...}}
                var itemsDict = result.items || {};
                var arr = [];
                Ext.iterate(itemsDict, function(k, v) { arr.push(v); });
                self._previewItems = arr;
                self.updatePreview();
            },
            function(err) {
                self._previewLoading = false;
                if (status) status.innerHTML = _('Failed to fetch: ') +
                    Ext.util.Format.htmlEncode((err && err.message) ? err.message : String(err));
            }
        );
    },

    // Re-filter the cached items against current regex fields and render.
    updatePreview: function() {
        var listEl = this.getPreviewListEl();
        var statusEl = this.getPreviewStatusEl();
        if (!listEl) return;

        if (!this._previewItems) {
            if (statusEl && !this._previewLoading) {
                statusEl.innerHTML = _('Select a feed above to see items.');
            }
            listEl.innerHTML = '';
            return;
        }

        var v = Deluge.ux.yarss2.readForm(this.form);
        var incRe = this._safeRegex(v.regex_include, !!v.regex_include_ignorecase);
        var excRe = this._safeRegex(v.regex_exclude, !!v.regex_exclude_ignorecase);

        // If include regex failed to compile, show the error.
        if (incRe && incRe.error) {
            statusEl.innerHTML = '<span style="color:#e25555">' +
                _('Include regex error: ') + Ext.util.Format.htmlEncode(incRe.error) + '</span>';
            listEl.innerHTML = '';
            return;
        }
        if (excRe && excRe.error) {
            statusEl.innerHTML = '<span style="color:#e25555">' +
                _('Exclude regex error: ') + Ext.util.Format.htmlEncode(excRe.error) + '</span>';
            listEl.innerHTML = '';
            return;
        }

        var items = this._previewItems;
        var matches = 0, excluded = 0;
        var rows = [];
        for (var i = 0; i < items.length; i++) {
            var title = items[i].title || '';
            var included = incRe ? incRe.re.test(title) : false;
            var isExcluded = included && excRe ? excRe.re.test(title) : false;
            var color = '#888';           // default: not matched
            var decoration = 'none';
            if (included && !isExcluded) { color = '#6ac26a'; matches++; }
            else if (included && isExcluded) { color = '#e25555'; decoration = 'line-through'; excluded++; }
            // Only show matched and excluded items when there's an include regex,
            // or show all items when the include regex is empty.
            if (incRe && !included) continue;
            rows.push('<div style="color:' + color + ';text-decoration:' + decoration + '">' +
                      Ext.util.Format.htmlEncode(title) + '</div>');
        }

        var summary;
        var total = items.length;
        if (!incRe) {
            summary = String.format(_('{0} items in feed. Type an include regex above to filter.'), total);
            // Show all items in gray when there's no regex yet.
            rows = items.map(function(it) {
                return '<div style="color:#aaa">' +
                       Ext.util.Format.htmlEncode(it.title || '') + '</div>';
            });
        } else if (excluded > 0) {
            summary = String.format(
                _('{0} of {1} items match (and {2} excluded).'),
                matches, total, excluded);
        } else {
            summary = String.format(
                _('{0} of {1} items match.'), matches, total);
        }
        statusEl.innerHTML = summary;
        listEl.innerHTML = rows.join('');
    },

    // Compile a JS RegExp safely. Returns { re: RegExp } or { error: msg }
    // or null for empty input.
    _safeRegex: function(pattern, ignoreCase) {
        if (!pattern) return null;
        try {
            return { re: new RegExp(pattern, ignoreCase ? 'i' : '') };
        } catch (e) {
            return { error: e.message };
        }
    },

    showForRecord: function(record, feeds) {
        this.editingRecord = record;
        this.setTitle(record ? _('Edit Subscription') : _('Add Subscription'));

        // Populate the feed combo from the feeds currently in config.
        this.feedStore.loadData(feeds.map(function(f) { return { key: f.key, name: f.name }; }));

        // Keep the full feed records keyed by id so fetchPreviewItems can
        // retrieve url/site/user_agent/etc. The combo store only has {key,name}.
        this._feedsByKey = {};
        var self = this;
        feeds.forEach(function(f) { self._feedsByKey[f.key] = f; });

        // Reset preview cache between opens.
        this._previewItems = null;
        this._previewLoading = false;

        var defaults = {
            name: '', rssfeed_key: feeds.length ? feeds[0].key : '',
            active: true,
            regex_include: '', regex_exclude: '',
            regex_include_ignorecase: true, regex_exclude_ignorecase: true,
            ignore_timestamp: false,
            download_location: '', move_completed: '', label: '',
            max_download_speed: -2, max_upload_speed: -2,
            max_connections: -2, max_upload_slots: -2
        };
        var values = Ext.apply(defaults, record || {});
        this.form.getForm().setValues(values);
        this._previewFeedKey = values.rssfeed_key;
        this.show();

        // Kick off the initial preview fetch after the window has rendered.
        // Deferring with setTimeout ensures the preview DOM is in place.
        setTimeout(function() {
            self.fetchPreviewItems(false);
        }, 50);
    },

    onSave: function() {
        var form = this.form.getForm();
        if (!form.isValid()) return;
        var v = Deluge.ux.yarss2.readForm(this.form);
        var rec = this.editingRecord || {};

        // Build a complete subscription payload. Fields not exposed here
        // (email_notifications, tri-state torrent options, custom_text_lines,
        // last_match) are preserved from the record if present, or defaulted.
        var data = {
            name: v.name,
            rssfeed_key: v.rssfeed_key,
            active: !!v.active,
            regex_include: v.regex_include || '',
            regex_exclude: v.regex_exclude || '',
            regex_include_ignorecase: !!v.regex_include_ignorecase,
            regex_exclude_ignorecase: !!v.regex_exclude_ignorecase,
            ignore_timestamp: !!v.ignore_timestamp,
            download_location: v.download_location || '',
            move_completed: v.move_completed || '',
            label: v.label || '',
            max_download_speed: parseInt(v.max_download_speed, 10),
            max_upload_speed:   parseInt(v.max_upload_speed, 10),
            max_connections:    parseInt(v.max_connections, 10),
            max_upload_slots:   parseInt(v.max_upload_slots, 10),
            last_match:         rec.last_match || '',
            custom_text_lines:  rec.custom_text_lines || '',
            email_notifications: rec.email_notifications || {},
            add_torrents_in_paused_state:   rec.add_torrents_in_paused_state   || 'Default',
            auto_managed:                   rec.auto_managed                   || 'Default',
            sequential_download:            rec.sequential_download            || 'Default',
            prioritize_first_last_pieces:   rec.prioritize_first_last_pieces   || 'Default'
        };
        if (rec.key !== undefined) data.key = rec.key;

        var self = this;
        Deluge.ux.yarss2.client().save_subscription(data.key || null, data, false).then(
            function() { self.hide(); self.fireEvent('yarss2-saved'); },
            function(err) { Deluge.ux.yarss2.errorAlert(_('Failed to save subscription'), err); }
        );
    },

    onCancel: function() { this.hide(); }
});

/* ------------------------------------------------------------------ *
 * Cookie edit window
 * ------------------------------------------------------------------ */

Deluge.ux.yarss2.CookieWindow = Ext.extend(Ext.Window, {
    title: _('Cookie'),
    width: 540,
    height: 440,
    layout: 'fit',
    modal: true,
    plain: true,
    closeAction: 'hide',

    initComponent: function() {
        Deluge.ux.yarss2.CookieWindow.superclass.initComponent.call(this);

        // Inner grid: name/value pairs. Editable cells.
        this.pairStore = new Ext.data.JsonStore({
            fields: ['k', 'v'], data: []
        });
        this.pairGrid = new Ext.grid.EditorGridPanel({
            store: this.pairStore, clicksToEdit: 1,
            region: 'center', height: 220,
            title: _('Name / Value pairs'),
            columns: [
                { header: _('Name'),  dataIndex: 'k', editor: { xtype: 'textfield' }, width: 200 },
                { header: _('Value'), dataIndex: 'v', editor: { xtype: 'textfield' }, flex: 1 }
            ],
            tbar: [
                { text: _('Add pair'), iconCls: 'x-deluge-add-window', handler: this.onAddPair, scope: this },
                { text: _('Remove'),   iconCls: 'icon-remove',          handler: this.onRemovePair, scope: this }
            ]
        });

        this.form = new Ext.form.FormPanel({
            border: false,
            bodyStyle: 'padding: 10px',
            labelWidth: 80,
            labelSeparator: ':',
            layout: 'border',
            items: [
                {
                    region: 'north', height: 80, border: false,
                    layout: 'form', defaults: { anchor: '100%' },
                    items: [
                        { xtype: 'textfield', fieldLabel: _('Site'), name: 'site',
                            allowBlank: false,
                            emptyText: _('e.g. tracker.example.com (bare host or URL)') },
                        { xtype: 'checkbox', fieldLabel: _('Active'), name: 'active', checked: true }
                    ]
                },
                this.pairGrid
            ]
        });
        this.add(this.form);

        this.saveBtn   = this.addButton({ text: _('Save'),   handler: this.onSave,   scope: this });
        this.cancelBtn = this.addButton({ text: _('Cancel'), handler: this.onCancel, scope: this });
    },

    showForRecord: function(record) {
        this.editingRecord = record;
        this.setTitle(record ? _('Edit Cookie') : _('Add Cookie'));
        var pairs = [];
        if (record && record.value) {
            Ext.iterate(record.value, function(k, v) { pairs.push({ k: k, v: v }); });
        }
        this.pairStore.loadData(pairs);
        this.form.getForm().setValues({
            site: (record && record.site) || '',
            active: record ? !!record.active : true
        });
        this.show();
    },

    onAddPair: function() {
        var RecType = this.pairStore.recordType;
        this.pairStore.add(new RecType({ k: '', v: '' }));
    },

    onRemovePair: function() {
        var sel = this.pairGrid.getSelectionModel().getSelected();
        if (sel) this.pairStore.remove(sel);
    },

    onSave: function() {
        var form = this.form.getForm();
        if (!form.isValid()) return;
        var v = Deluge.ux.yarss2.readForm(this.form);

        // Flatten the pair grid into a {k: v} dict. Empty keys are dropped.
        var value = {};
        this.pairStore.each(function(rec) {
            var k = (rec.get('k') || '').trim();
            if (k) value[k] = rec.get('v') || '';
        });
        if (Object.keys(value).length === 0) {
            Ext.Msg.alert(_('Invalid'), _('At least one name/value pair is required.'));
            return;
        }

        var data = {
            site: v.site, active: !!v.active, value: value
        };
        if (this.editingRecord && this.editingRecord.key !== undefined) {
            data.key = this.editingRecord.key;
        }
        var self = this;
        Deluge.ux.yarss2.client().save_cookie(data.key || null, data, false).then(
            function() { self.hide(); self.fireEvent('yarss2-saved'); },
            function(err) { Deluge.ux.yarss2.errorAlert(_('Failed to save cookie'), err); }
        );
    },

    onCancel: function() { this.hide(); }
});

/* ------------------------------------------------------------------ *
 * Generic CRUD grid base — feeds, subscriptions, cookies all derive from it.
 * ------------------------------------------------------------------ */

Deluge.ux.yarss2.CrudGrid = Ext.extend(Ext.grid.GridPanel, {
    // Subclasses fill in: columns, makeStore, openEdit, deleteApi, recordLabel,
    // extractDict, and optionally extraButtons.

    initComponent: function() {
        this.store = this.makeStore();

        var tbar = [
            { text: _('Add'),    iconCls: 'x-deluge-add-window', handler: this.onAdd,    scope: this },
            { text: _('Edit'),   iconCls: 'icon-edit-trackers',  handler: this.onEdit,   scope: this },
            { text: _('Delete'), iconCls: 'icon-remove',         handler: this.onDelete, scope: this }
        ];
        if (this.extraButtons) tbar = tbar.concat(this.extraButtons);

        Ext.apply(this, {
            sm: new Ext.grid.RowSelectionModel({ singleSelect: true }),
            viewConfig: { forceFit: true },
            tbar: tbar
        });
        Deluge.ux.yarss2.CrudGrid.superclass.initComponent.call(this);
        this.on('rowdblclick', this.onEdit, this);
    },

    reload: function(config) {
        this.currentConfig = config;
        var rows = Deluge.ux.yarss2.dictToRows(this.extractDict(config));
        // Inactive tabs aren't rendered yet — defer until they are, otherwise
        // the store's datachanged event crashes GridView.refresh().
        if (this.rendered) {
            this.store.loadData(rows);
        } else {
            this.on('render', function() { this.store.loadData(rows); },
                    this, { single: true });
        }
    },

    selected: function() {
        var rec = this.getSelectionModel().getSelected();
        return rec ? rec.data : null;
    },

    onAdd:  function() { this.openEdit(null); },
    onEdit: function() {
        var sel = this.selected();
        if (!sel) return Ext.Msg.alert(_('No selection'), _('Pick a row first.'));
        this.openEdit(sel);
    },
    onDelete: function() {
        var self = this, sel = this.selected();
        if (!sel) return;
        Deluge.ux.yarss2.confirm(_('Delete?'),
            String.format(_('Delete {0} "{1}"? This cannot be undone.'),
                          this.recordLabel, sel.name || ''),
            function() {
                self.deleteApi(sel.key).then(
                    function() { self.fireEvent('yarss2-changed'); },
                    function(err) { Deluge.ux.yarss2.errorAlert(_('Delete failed'), err); }
                );
            });
    }
});

/* ------------------------------------------------------------------ *
 * Feeds grid
 * ------------------------------------------------------------------ */

Deluge.ux.yarss2.FeedsGrid = Ext.extend(Deluge.ux.yarss2.CrudGrid, {
    title: _('RSS Feeds'),
    recordLabel: _('feed'),

    extractDict: function(c) { return c.rssfeeds || {}; },
    deleteApi: function(key) {
        return Deluge.ux.yarss2.client().save_rssfeed(key, null, true);
    },

    makeStore: function() {
        return new Ext.data.JsonStore({
            fields: ['key', 'name', 'url', 'site', 'active', 'update_interval',
                     'last_update', 'verify_tls', 'obey_ttl', 'update_on_startup',
                     'prefer_magnet', 'user_agent', 'etag', 'last_modified'],
            data: []
        });
    },

    columns: [
        { header: _('Active'), dataIndex: 'active', width: 55,
            renderer: function(v) { return v ? '✓' : ''; } },
        { header: _('Name'),   dataIndex: 'name',   width: 180 },
        { header: _('URL'),    dataIndex: 'url',    flex: 1 },
        { header: _('Every'),  dataIndex: 'update_interval', width: 70,
            renderer: function(v) { return v + ' min'; } },
        { header: _('Last update'), dataIndex: 'last_update', width: 140 },
        { header: _('TLS'), dataIndex: 'verify_tls', width: 50,
            renderer: function(v) { return v === false ? '⚠ off' : 'on'; } }
    ],

    initComponent: function() {
        var self = this;
        this.extraButtons = [
            '-',
            { text: _('Run now'), iconCls: 'icon-update',
              handler: function() {
                  var sel = self.selected();
                  if (!sel) return;
                  Deluge.ux.yarss2.client().initiate_rssfeed_update(sel.key, null).then(
                      function() { Ext.Msg.alert(_('YaRSS2'), _('Feed fetch queued.')); },
                      function(err) { Deluge.ux.yarss2.errorAlert(_('Run failed'), err); }
                  );
              } }
        ];
        Deluge.ux.yarss2.FeedsGrid.superclass.initComponent.call(this);
    },

    openEdit: function(record) {
        if (!this.editWin) {
            this.editWin = new Deluge.ux.yarss2.RssFeedWindow();
            this.editWin.on('yarss2-saved', function() { this.fireEvent('yarss2-changed'); }, this);
        }
        this.editWin.showForRecord(record);
    }
});

/* ------------------------------------------------------------------ *
 * Subscriptions grid
 * ------------------------------------------------------------------ */

Deluge.ux.yarss2.SubscriptionsGrid = Ext.extend(Deluge.ux.yarss2.CrudGrid, {
    title: _('Subscriptions'),
    recordLabel: _('subscription'),
    extractDict: function(c) { return c.subscriptions || {}; },
    deleteApi: function(key) {
        return Deluge.ux.yarss2.client().save_subscription(key, null, true);
    },

    makeStore: function() {
        return new Ext.data.JsonStore({
            fields: ['key', 'name', 'rssfeed_key', 'active',
                     'regex_include', 'regex_exclude',
                     'regex_include_ignorecase', 'regex_exclude_ignorecase',
                     'ignore_timestamp', 'download_location', 'move_completed',
                     'label', 'last_match',
                     'max_download_speed', 'max_upload_speed',
                     'max_connections', 'max_upload_slots',
                     'add_torrents_in_paused_state', 'auto_managed',
                     'sequential_download', 'prioritize_first_last_pieces',
                     'email_notifications', 'custom_text_lines'],
            data: []
        });
    },

    columns: [
        { header: _('Active'),  dataIndex: 'active', width: 55,
            renderer: function(v) { return v ? '✓' : ''; } },
        { header: _('Name'),    dataIndex: 'name', width: 180 },
        { header: _('Feed'),    dataIndex: 'rssfeed_key', width: 140 },
        { header: _('Include'), dataIndex: 'regex_include', flex: 1 },
        { header: _('Exclude'), dataIndex: 'regex_exclude', flex: 1 },
        { header: _('Last match'), dataIndex: 'last_match', width: 140 }
    ],

    openEdit: function(record) {
        if (!this.editWin) {
            this.editWin = new Deluge.ux.yarss2.SubscriptionWindow();
            this.editWin.on('yarss2-saved', function() { this.fireEvent('yarss2-changed'); }, this);
        }
        var feeds = Deluge.ux.yarss2.dictToRows(this.currentConfig.rssfeeds);
        if (!feeds.length) {
            return Ext.Msg.alert(_('No feeds'),
                _('Add at least one RSS feed before creating a subscription.'));
        }
        this.editWin.showForRecord(record, feeds);
    },

    reload: function(config) {
        Deluge.ux.yarss2.SubscriptionsGrid.superclass.reload.call(this, config);
        // Swap the feed-key column renderer once we have feed names in hand.
        var feedsById = {};
        Ext.iterate(config.rssfeeds || {}, function(k, v) {
            feedsById[v.key !== undefined ? v.key : k] = v.name;
        });
        var cm = this.getColumnModel();
        for (var i = 0; i < cm.getColumnCount(); i++) {
            if (cm.getDataIndex(i) === 'rssfeed_key') {
                cm.setRenderer(i, function(v) { return feedsById[v] || v || ''; });
            }
        }
        if (this.rendered && this.getView()) this.getView().refresh();
    }
});

/* ------------------------------------------------------------------ *
 * Cookies grid
 * ------------------------------------------------------------------ */

Deluge.ux.yarss2.CookiesGrid = Ext.extend(Deluge.ux.yarss2.CrudGrid, {
    title: _('Cookies'),
    recordLabel: _('cookie'),
    extractDict: function(c) { return c.cookies || {}; },
    deleteApi: function(key) {
        return Deluge.ux.yarss2.client().save_cookie(key, null, true);
    },

    makeStore: function() {
        return new Ext.data.JsonStore({
            fields: ['key', 'site', 'active', 'value'], data: []
        });
    },

    columns: [
        { header: _('Active'), dataIndex: 'active', width: 55,
            renderer: function(v) { return v ? '✓' : ''; } },
        { header: _('Site'),   dataIndex: 'site',  width: 240 },
        { header: _('Names'),  dataIndex: 'value', flex: 1,
            renderer: function(v) { return v ? Object.keys(v).join(', ') : ''; } }
    ],

    openEdit: function(record) {
        if (!this.editWin) {
            this.editWin = new Deluge.ux.yarss2.CookieWindow();
            this.editWin.on('yarss2-saved', function() { this.fireEvent('yarss2-changed'); }, this);
        }
        this.editWin.showForRecord(record);
    }
});

/* ------------------------------------------------------------------ *
 * General settings tab
 * ------------------------------------------------------------------ */

Deluge.ux.yarss2.GeneralPanel = Ext.extend(Ext.form.FormPanel, {
    title: _('General'),
    border: false,
    bodyStyle: 'padding: 15px',
    labelWidth: 220,
    labelSeparator: ':',

    initComponent: function() {
        Deluge.ux.yarss2.GeneralPanel.superclass.initComponent.call(this);
        this.add([
            {
                xtype: 'numberfield',
                fieldLabel: _('Max concurrent feed fetches'),
                name: 'max_concurrent_feeds', value: 1, minValue: 1, width: 80
            },
            {
                xtype: 'checkbox',
                fieldLabel: _('Show log panel in GTK client'),
                name: 'show_log_in_gui',
                boxLabel: _('Only affects the GTK client')
            },
            {
                xtype: 'panel', border: false, bodyStyle: 'padding-top: 20px',
                html: '<p><b>' + _('Not yet available in WebUI:') + '</b> ' +
                      _('Email notifications and message templates. Use the GTK client for those.') +
                      '</p>'
            }
        ]);
        this.addButton({ text: _('Save'), handler: this.onSave, scope: this });
    },

    reload: function(config) {
        var g = (config.general || {});
        this.getForm().setValues({
            max_concurrent_feeds: g.max_concurrent_feeds != null ? g.max_concurrent_feeds : 1,
            show_log_in_gui: g.show_log_in_gui !== false
        });
    },

    onSave: function() {
        var v = Deluge.ux.yarss2.readForm(this);
        var payload = {
            max_concurrent_feeds: parseInt(v.max_concurrent_feeds, 10) || 1,
            show_log_in_gui: !!v.show_log_in_gui
        };
        Deluge.ux.yarss2.client().save_general_config(payload).then(
            function() { Ext.Msg.alert(_('YaRSS2'), _('General settings saved.')); },
            function(err) { Deluge.ux.yarss2.errorAlert(_('Save failed'), err); }
        );
    }
});

/* ------------------------------------------------------------------ *
 * Log tab — polls the YaRSS2 core's in-memory ring buffer and renders
 * recent log messages in a scrolling <pre>. Polling pauses when the
 * user toggles the Pause button; the tab keeps polling while hidden
 * so when the user switches to it, recent history is already there.
 * ------------------------------------------------------------------ */

Deluge.ux.yarss2.LogPanel = Ext.extend(Ext.Panel, {
    title: _('Log'),
    layout: 'fit',
    border: false,
    cls: 'yarss2-log-panel',

    lastId: 0,
    pollInterval: 3000,
    levelFilter: 'ALL',
    paused: false,

    initComponent: function() {
        var self = this;

        this.levelCombo = new Ext.form.ComboBox({
            store: new Ext.data.ArrayStore({
                fields: ['v', 'n'],
                data: [['ALL', _('All levels')],
                       ['INFO', 'INFO and above'],
                       ['WARNING', _('WARNING and above')],
                       ['ERROR', _('ERROR only')]]
            }),
            valueField: 'v', displayField: 'n',
            mode: 'local', triggerAction: 'all',
            editable: false, width: 180,
            value: 'ALL'
        });
        this.levelCombo.on('select', function(cb, rec) {
            self.levelFilter = rec.get('v');
            self.redraw();
        });

        this.pauseBtn = new Ext.Toolbar.Button({
            text: _('Pause'), iconCls: 'icon-pause',
            enableToggle: true,
            toggleHandler: function(btn, pressed) {
                self.paused = pressed;
                btn.setText(pressed ? _('Resume') : _('Pause'));
            }
        });

        this.clearBtn = new Ext.Toolbar.Button({
            text: _('Clear'), iconCls: 'icon-remove',
            handler: function() {
                Deluge.ux.yarss2.confirm(
                    _('Clear log'),
                    _('Clear all buffered log messages? This only affects the in-memory buffer shown here; the daemon log file is unaffected.'),
                    function() {
                        Deluge.ux.yarss2.client().clear_log_messages().then(
                            function() {
                                self.entries = [];
                                self.lastId = 0;
                                self.redraw();
                            },
                            function(err) { Deluge.ux.yarss2.errorAlert(_('Clear failed'), err); }
                        );
                    }
                );
            }
        });

        this.autoScrollCheck = new Ext.form.Checkbox({
            boxLabel: _('Auto-scroll'), checked: true,
            listeners: { check: function(cb, v) { self.autoScroll = v; } }
        });
        this.autoScroll = true;

        Ext.apply(this, {
            tbar: [_('Level:'), ' ', this.levelCombo,
                   ' ', this.pauseBtn, ' ', this.clearBtn,
                   '->', this.autoScrollCheck],
            html: '<pre class="yarss2-log-body" style="margin:0;padding:8px;' +
                  'font-family:Menlo,Consolas,monospace;font-size:11px;' +
                  'line-height:1.35;white-space:pre-wrap;word-break:break-word;' +
                  'height:100%;overflow:auto;"></pre>'
        });

        Deluge.ux.yarss2.LogPanel.superclass.initComponent.call(this);

        this.entries = [];
        this.maxClientEntries = 2000;

        this.on('afterrender', this.startPolling, this);
        this.on('beforedestroy', this.stopPolling, this);
    },

    getBodyEl: function() {
        var el = this.body ? this.body.dom : null;
        if (!el) return null;
        return el.querySelector('pre.yarss2-log-body');
    },

    startPolling: function() {
        var self = this;
        if (this._timer) return;
        this._timer = setInterval(function() { self.poll(); }, this.pollInterval);
        this.poll();
    },

    stopPolling: function() {
        if (this._timer) {
            clearInterval(this._timer);
            this._timer = null;
        }
    },

    poll: function() {
        if (this.paused) return;
        if (!this.rendered) return;
        var self = this;
        Deluge.ux.yarss2.client().get_log_messages(this.lastId, 500).then(
            function(result) {
                if (!result || !result.items) return;
                if (result.items.length > 0) {
                    self.entries = self.entries.concat(result.items);
                    if (self.entries.length > self.maxClientEntries) {
                        self.entries = self.entries.slice(-self.maxClientEntries);
                    }
                    self.lastId = result.items[result.items.length - 1].id;
                    self.redraw();
                }
            },
            function(err) {
                if (window.console) console.warn('YaRSS2 log poll failed:', err);
            }
        );
    },

    levelMatches: function(level) {
        if (this.levelFilter === 'ALL') return true;
        if (this.levelFilter === 'INFO') return ['INFO','WARNING','ERROR','CRITICAL'].indexOf(level) !== -1;
        if (this.levelFilter === 'WARNING') return ['WARNING','ERROR','CRITICAL'].indexOf(level) !== -1;
        if (this.levelFilter === 'ERROR') return ['ERROR','CRITICAL'].indexOf(level) !== -1;
        return true;
    },

    formatEntry: function(e) {
        var when = new Date(e.time * 1000);
        var hh = ('0' + when.getHours()).slice(-2);
        var mm = ('0' + when.getMinutes()).slice(-2);
        var ss = ('0' + when.getSeconds()).slice(-2);
        var ts = hh + ':' + mm + ':' + ss;
        var level = String(e.level || 'INFO');
        var color = 'inherit';
        if (level === 'WARNING') color = '#d9a441';
        else if (level === 'ERROR' || level === 'CRITICAL') color = '#e25555';
        else if (level === 'DEBUG') color = '#888';
        // Strip the python Formatter prefix so the line isn't double-timestamped.
        // Expected format: "HH:MM:SS [LEVEL] logger: message"
        var msg = e.message || '';
        var m = msg.match(/^\d{2}:\d{2}:\d{2}\s+\[[A-Z]+\]\s+\S+:\s+([\s\S]*)$/);
        if (m) msg = m[1];
        return '<span style="color:' + color + '">' +
               ts + ' [' + level + '] ' +
               Ext.util.Format.htmlEncode(msg) +
               '</span>';
    },

    redraw: function() {
        var el = this.getBodyEl();
        if (!el) return;
        var self = this;
        var html = this.entries
            .filter(function(e) { return self.levelMatches(e.level); })
            .map(function(e) { return self.formatEntry(e); })
            .join('\n');
        el.innerHTML = html;
        if (this.autoScroll) {
            el.scrollTop = el.scrollHeight;
        }
    },

    reload: function(_config) {
        // Triggered when the page (re-)shows. Force an immediate poll.
        this.poll();
    }
});

/* ------------------------------------------------------------------ *
 * Preferences page — the top-level container.
 * ------------------------------------------------------------------ */

Deluge.ux.preferences.YaRSS2Page = Ext.extend(Ext.Panel, {
    title: _('YaRSS2'),
    header: false,
    border: false,
    layout: 'fit',

    initComponent: function() {
        Deluge.ux.preferences.YaRSS2Page.superclass.initComponent.call(this);

        this.feedsGrid   = new Deluge.ux.yarss2.FeedsGrid();
        this.subsGrid    = new Deluge.ux.yarss2.SubscriptionsGrid();
        this.cookiesGrid = new Deluge.ux.yarss2.CookiesGrid();
        this.generalTab  = new Deluge.ux.yarss2.GeneralPanel();
        this.logTab      = new Deluge.ux.yarss2.LogPanel();

        var self = this;
        [this.feedsGrid, this.subsGrid, this.cookiesGrid].forEach(function(g) {
            g.on('yarss2-changed', self.reload, self);
        });

        this.tabs = new Ext.TabPanel({
            activeTab: 0, border: false,
            enableTabScroll: true,
            resizeTabs: true, minTabWidth: 90, tabWidth: 110,
            items: [this.feedsGrid, this.subsGrid, this.cookiesGrid,
                    this.generalTab, this.logTab]
        });
        this.add(this.tabs);

        // Refresh whenever the preferences page becomes visible.
        this.on('show', this.reload, this);
    },

    reload: function() {
        var self = this;
        Deluge.ux.yarss2.client().get_config().then(
            function(config) {
                self.currentConfig = config;
                self.feedsGrid.reload(config);
                self.subsGrid.reload(config);
                self.cookiesGrid.reload(config);
                self.generalTab.reload(config);
                if (self.logTab && self.logTab.reload) self.logTab.reload(config);
            },
            function(err) { Deluge.ux.yarss2.errorAlert(_('Could not load YaRSS2 config'), err); }
        );
    }
});

/* ------------------------------------------------------------------ *
 * Plugin boilerplate
 * ------------------------------------------------------------------ */

Deluge.plugins.YaRSS2Plugin = Ext.extend(Deluge.Plugin, {
    name: 'YaRSS2',

    onDisable: function() {
        deluge.preferences.removePage(this.prefsPage);
    },

    onEnable: function() {
        this.prefsPage = deluge.preferences.addPage(
            new Deluge.ux.preferences.YaRSS2Page()
        );
    }
});

Deluge.registerPlugin('YaRSS2', Deluge.plugins.YaRSS2Plugin);
