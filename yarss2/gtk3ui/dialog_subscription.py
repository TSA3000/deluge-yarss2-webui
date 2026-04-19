# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2015 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#
import html

import deluge.component as component
from deluge.ui.client import client

from yarss2.gtk3ui.path_chooser import PathChooser
from yarss2.rssfeed_handling import RSSFeedHandler
from yarss2.util import http
from yarss2.util.common import (GeneralSubsConf, TorrentDownload, get_current_date_in_isoformat, get_resource,
                                get_value_in_selected_row)
from yarss2.yarss_config import get_user_agent

from .CellRendererPango import CellRendererPango, CustomAttribute
from .common import Gdk, GdkPixbuf, Gtk, get_selected_combobox_key, set_tooltip_markup


class DialogSubscriptionGUI(object):

    def __init__(self, editing=False, new_subscription=False):
        self.editing = editing
        self.new_subscription = new_subscription
        self.matching_store = None
        self.icon_matching = GdkPixbuf.Pixbuf.new_from_file(get_resource("match.png"))
        self.icon_nonmatching = GdkPixbuf.Pixbuf.new_from_file(get_resource("no_match.png"))
        self.labels = None

    def setup_gui(self):
        self.glade = Gtk.Builder.new_from_file(get_resource("dialog_subscription.ui"))
        self.glade.connect_signals({
            "on_txt_regex_include_changed": self.on_txt_regex_changed,
            "on_txt_regex_exclude_changed": self.on_txt_regex_changed,
            "on_check_regex_include_toggled": self.on_txt_regex_changed,
            "on_check_regex_exclude_toggled": self.on_txt_regex_changed,
            "on_button_cancel_clicked": self.on_button_cancel_clicked,
            "on_button_destroy_clicked": self.on_button_cancel_clicked,
            "on_button_save_clicked": self.on_button_save_subscription_clicked,
            "on_button_add_notication_clicked": self.on_button_add_notication_clicked,
            "on_button_remove_notication_clicked": self.on_button_remove_notication_clicked,
            "on_rssfeed_selected": self.on_rssfeed_selected,
            "on_button_fetch_clicked": self.on_rssfeed_selected,
            "on_button_last_matched_reset_clicked": self.on_button_last_matched_reset_clicked,
            "on_button_last_matched_now_clicked": self.on_button_last_matched_now_clicked,
            "on_general_checkbox_toggled": self.on_general_checkbox_toggled,
            "on_key_pressed": self.on_key_pressed,
            "on_textview_custom_text_move_cursor": lambda x, y: x,
            "on_panel_matching_move_handle": lambda x, y: x,
            "on_dialog_subscription_response": self.on_dialog_subscription_response_signal,
            "on_txt_filter_include_query_tooltip": self.on_txt_filter_include_query_tooltip,
            "on_txt_filter_exclude_query_tooltip": self.on_txt_filter_exclude_query_tooltip,
        })

        self.dialog = self.get_object("dialog_subscription")
        self.dialog.set_title("Edit Subscription" if self.editing else "Add Subscription")

        self.setup_rssfeed_combobox()
        self.setup_move_completed_combobox()
        self.setup_download_location_combobox()
        self.setup_messages_combobox()
        self.setup_messages_list()
        self.treeview = self.create_matching_tree()
        self.setup_labels()
        self.set_custom_text_tooltip()

    def get_object(self, name):
        return self.glade.get_object(name)

    def on_dialog_subscription_response_signal(self, widget, arg):
        # Escape key or close button (X in corner)
        if arg == -4:
            self.destroy()

    def destroy(self):
        component.get("Preferences").pref_dialog.set_modal(True)
        self.dialog.destroy()

    def show_dialog(self):
        pref_dialog = component.get("Preferences").pref_dialog
        self.dialog.set_transient_for(pref_dialog)
        # Disable modality for Preferences to allow managing the torrent list while
        # this dialog is opened
        pref_dialog.set_modal(False)
        self.dialog.show()

    def get_current_rssfeed_key(self):
        return get_selected_combobox_key(self.get_object("combobox_rssfeeds"))

    def setup_labels(self):
        combobox_labels = self.get_object("combobox_labels")
        label_labels = self.get_object("labels_label")

        def on_labels(labels):
            self.labels = labels
            # Disable labels in GUI
            if self.labels is None:
                label_labels.set_sensitive(False)
                combobox_labels.set_sensitive(False)
                tooltips = Gtk.Tooltips()
                tooltips.set_tip(combobox_labels, 'Label plugin is not enabled')
            else:
                label_labels.set_sensitive(True)
                renderer_label = Gtk.CellRendererText()
                combobox_labels.pack_end(renderer_label, False)
                combobox_labels.add_attribute(renderer_label, "text", 0)
                self.labels_liststore = Gtk.ListStore(str)
                combobox_labels.set_model(self.labels_liststore)

        self.get_labels_d = self.gtkUI.get_labels().addCallback(on_labels)

    def setup_move_completed_combobox(self):
        move_completed_box = self.get_object("move_completed_box")
        self.move_completed_path_chooser = PathChooser("move_completed_paths_list")
        self.move_completed_path_chooser.set_filechooser_button_visible(client.is_localhost())
        self.move_completed_path_chooser.set_enable_properties(False)
        self.move_completed_path_chooser.set_enable_properties(True)
        move_completed_box.add(self.move_completed_path_chooser)
        move_completed_box.show_all()

    def setup_download_location_combobox(self):
        download_location_box = self.get_object("download_location_box")
        self.download_location_path_chooser = PathChooser("download_location_paths_list")
        self.download_location_path_chooser.set_filechooser_button_visible(client.is_localhost())
        download_location_box.add(self.download_location_path_chooser)
        download_location_box.show_all()

    def setup_rssfeed_combobox(self):
        rssfeeds_combobox = self.get_object("combobox_rssfeeds")
        renderer_name = Gtk.CellRendererText()
        renderer_site = Gtk.CellRendererText()
        rssfeeds_combobox.pack_start(renderer_name, False)
        rssfeeds_combobox.pack_end(renderer_site, False)
        rssfeeds_combobox.add_attribute(renderer_name, "text", 1)
        rssfeeds_combobox.add_attribute(renderer_site, "text", 2)
        # key, name, site url
        self.rssfeeds_store = Gtk.ListStore(str, str, str)
        rssfeeds_combobox.set_model(self.rssfeeds_store)

    def setup_messages_combobox(self):
        messages_combobox = self.get_object("combobox_messages")
        renderer_text = Gtk.CellRendererText()
        messages_combobox.pack_start(renderer_text, False)
        messages_combobox.add_attribute(renderer_text, "text", 1)

        # key, name
        self.messages_combo_store = Gtk.ListStore(str, str)
        messages_combobox.set_model(self.messages_combo_store)

    def setup_messages_list(self):
        # message_key, message_title, active, torrent_added, torrent_completed,
        self.messages_list_store = Gtk.ListStore(str, str, bool, bool, bool)
        self.messages_treeview = Gtk.TreeView(model=self.messages_list_store)
        self.messages_treeview.connect("row-activated", self.on_notification_list_clicked)
        self.columns_dict = {}

        def cell_data_func(tree_column, cell, model, tree_iter):
            if model.get_value(tree_iter, 2) is True:
                pixbuf = self.icon_matching
            else:
                pixbuf = self.icon_nonmatching
            cell.set_property("pixbuf", pixbuf)

        renderer = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn("Message Active", renderer)
        column.set_cell_data_func(renderer, cell_data_func)
        self.messages_treeview.append_column(column)

        renderer_text = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Message Title", renderer_text, text=1)
        self.messages_treeview.append_column(column)

        renderer = Gtk.CellRendererToggle()
        renderer.connect("toggled", self.on_message_checkbox_toggled, self.messages_list_store)
        column = Gtk.TreeViewColumn("On torrent added", renderer, active=3)
        self.columns_dict["3"] = column
        self.messages_treeview.append_column(column)

        renderer = Gtk.CellRendererToggle()
        renderer.connect("toggled", self.on_message_checkbox_toggled, self.messages_list_store)
        column = Gtk.TreeViewColumn("On torrent completed", renderer, active=4)
        self.columns_dict["4"] = column

        viewport = self.get_object("viewport_email_notifications")
        viewport.add(self.messages_treeview)
        viewport.show_all()

    def create_matching_tree(self):
        # Matches, Title, Published, link, CustomAttribute for PangoCellrenderer, torrent link, magnet link
        self.matching_store = Gtk.ListStore(bool, str, str, str, CustomAttribute, str, str, int)

        self.matching_treeview = Gtk.TreeView(model=self.matching_store)
        self.matching_treeview.connect('button-press-event', self.on_matches_list_button_press_event)

        self.matching_treeview.connect('query-tooltip', self.on_tooltip_matches)
        self.matching_treeview.set_has_tooltip(True)

        def cell_data_func(tree_column, cell, model, tree_iter, *args):
            if model.get_value(tree_iter, 0) is True:
                pixbuf = self.icon_matching
            else:
                pixbuf = self.icon_nonmatching
            cell.set_property("pixbuf", pixbuf)

        renderer = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn("Matches", renderer)
        column.set_cell_data_func(renderer, cell_data_func)
        column.set_sort_column_id(0)
        self.matching_treeview.append_column(column)

        cellrenderer = CellRendererPango()
        column = Gtk.TreeViewColumn("Title", cellrenderer, text=1)
        column.add_attribute(cellrenderer, "custom", 4)
        column.set_sort_column_id(1)
        column.set_resizable(True)
        column.set_expand(True)
        self.matching_treeview.append_column(column)

        cellrenderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Published", cellrenderer, text=2)
        column.set_sort_column_id(2)
        self.matching_treeview.append_column(column)

        col = Gtk.TreeViewColumn()
        col.set_visible(False)
        self.matching_treeview.append_column(col)

        self.list_popup_menu = Gtk.Menu()
        menuitem1 = Gtk.MenuItem(label="Add torrent")
        menuitem1.connect("activate", self.on_button_add_torrent_clicked)
        menuitem2 = Gtk.MenuItem(label="Add torrent with current subscription options")
        menuitem2.connect("activate", self.on_button_add_torrent_clicked, True)
        menuitem3 = Gtk.MenuItem(label="Copy title to clipboard")
        menuitem3.connect("activate", self.on_button_copy_to_clipboard, 1)
        menuitem4 = Gtk.MenuItem(label="Copy link to clipboard")
        menuitem4.connect("activate", self.on_button_copy_to_clipboard, 3)

        self.list_popup_menu.append(menuitem1)
        self.list_popup_menu.append(menuitem2)
        self.list_popup_menu.append(menuitem3)
        self.list_popup_menu.append(menuitem4)
        return self.matching_treeview

    def on_general_checkbox_toggled(self, button):
        self.get_object("checkbox_add_torrents_in_paused_state").set_sensitive(
            not self.get_object("checkbox_add_torrents_in_paused_state_default").get_active())
        self.get_object("checkbutton_auto_managed").set_sensitive(
            not self.get_object("checkbutton_auto_managed_default").get_active())
        self.get_object("checkbutton_sequential_download").set_sensitive(
            not self.get_object("checkbutton_sequential_download_default").get_active())
        self.get_object("checkbutton_prioritize_first_last").set_sensitive(
            not self.get_object("checkbutton_prioritize_first_last_default").get_active())

    def on_button_copy_to_clipboard(self, menuitem, index):
        text = get_value_in_selected_row(self.matching_treeview,
                                         self.matching_store, column_index=index)
        if text is not None:
            Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(text, -1)

    def on_txt_filter_include_query_tooltip(self, widget, x, y, keyboard_mode, tooltip):
        return set_tooltip_markup(tooltip,
                                  ("Input a regex filter to match the titles to be included. "
                                   "See YaRSS2 Wiki page for help and examples"))

    def on_txt_filter_exclude_query_tooltip(self, widget, x, y, keyboard_mode, tooltip):
        return set_tooltip_markup(tooltip,
                                  ("Input a regex filter to match the titles to be excluded. "
                                   "See YaRSS2 Wiki page for help and examples"))

    def set_custom_text_tooltip(self):
        textview = self.get_object("textview_custom_text")
        textview.set_tooltip_text("Each line is added to the list and tested for matching against the filters.")

    def on_tooltip_matches(self, widget, x, y, keyboard_tip, tooltip):
        x, y = self.treeview.convert_widget_to_bin_window_coords(x, y)
        if widget.get_path_at_pos(x, y) is None:
            return False
        path, tree_column, t, r = widget.get_path_at_pos(x, y)
        if not path:
            return False
        # Matches, Title, Published, torrent link, CustomAttribute for PangoCellrenderer
        it = self.matching_store.get_iter(path)
        title = self.matching_store.get_value(it, 1)
        published = self.matching_store.get_value(it, 2)
        link = self.matching_store.get_value(it, 3)
        if link is None:
            return False

        rssfeed_key = self.get_current_rssfeed_key()
        rssfeed = self.rssfeeds[rssfeed_key]
        prefer_magnet = rssfeed['prefer_magnet']

        torrent_key = self.matching_store.get_value(it, 7)
        magnet = self.rssfeeds_dict[torrent_key]['magnet']
        torrent = self.rssfeeds_dict[torrent_key]['torrent']

        tooltip_text = ("<b>Title:</b> %s\n<b>Published:</b> %s" %
                        (html.escape(title), published))

        def add_html_tag(text, tag, add=True):
            if add is False:
                return text
            return "<{tag}>{text}</{tag}>".format(text=text, tag=tag)

        if torrent is not None:
            tooltip_text += "\n<b>Torrent: </b> %s" % (add_html_tag(html.escape(torrent), 'u', add=not prefer_magnet))
        if magnet is not None:
            tooltip_text += "\n<b>Magnet: </b> %s" % (add_html_tag(html.escape(magnet), 'u', add=prefer_magnet))

        tooltip.set_markup(tooltip_text)
        widget.set_tooltip_cell(tooltip, path, None, None)
        return True

    def on_matches_list_button_press_event(self, treeview, event):
        """Shows popup on selected row when right clicking"""
        if event.button == 3:
            pthinfo = treeview.get_path_at_pos(int(event.x), int(event.y))
            it = self.matching_store.get_iter(pthinfo[0])
            link = self.matching_store.get_value(it, 3)
            if link is None:
                return False

            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor(path, col, 0)
                self.list_popup_menu.popup(None, None, None, None, event.button, event.time)
                self.list_popup_menu.show_all()
            return True

    def set_matching_result_in_textview(self, result):
        """
        Insert the result in a textview and place in matching window
        """
        textview = Gtk.TextView()
        textbuffer = textview.get_buffer()
        textview.show()
        textbuffer.set_text(result)
        self.set_matching_window_child(textview)

    def set_matching_window_child(self, widget):
        """Insert the widget into the matching window"""
        matching_window = self.get_object("matching_window_upper")
        if matching_window.get_child():
            matching_window.remove(matching_window.get_child())
        matching_window.add(widget)

        # Quick hack to make sure the list of torrents are visible to the user.
        hpaned = self.get_object("hpaned_matching")
        if hpaned.get_position() == 0:
            max_pos = hpaned.get_property("max-position")
            hpaned.set_position(int(max_pos * 0.75))
        matching_window.show_all()

################
# Notifications
################

    def on_notification_list_clicked(self, event=None, a=None, col=None):
        """Callback for when the checkboxes (or actually just the row)
        in notification list is clicked"""
        tree, row_iter = self.messages_treeview.get_selection().get_selected()
        if not row_iter or not col:
            return
        for column in self.columns_dict.keys():
            if self.columns_dict[column] == col:
                column = int(column)
                val = self.messages_list_store.get_value(row_iter, column)
                self.messages_list_store.set_value(row_iter, column, not val)
                return

    def on_button_add_notication_clicked(self, button):
        combobox = self.get_object("combobox_messages")
        key = get_selected_combobox_key(combobox)
        if key is None:
            return
        # Current notications
        message_dict = self.get_current_notifications()
        for c_key in message_dict.keys():
            # This message is already in the notifications list
            if c_key == key:
                return
        self.messages_list_store.append([key, self.email_messages[key]["name"],
                                         self.email_messages[key]["active"], True, False])

    def get_current_notifications(self):
        """ Retrieves the notifications from the notifications list"""
        notifications = {}
        row_iter = self.messages_list_store.get_iter_first()
        while row_iter is not None:
            key = self.messages_list_store.get_value(row_iter, 0)
            # active = self.messages_list_store.get_value(row_iter, 2)
            on_added = self.messages_list_store.get_value(row_iter, 3)
            on_completed = self.messages_list_store.get_value(row_iter, 4)
            notifications[key] = {"on_torrent_added": on_added,
                                  "on_torrent_completed": on_completed}
            # Next row
            row_iter = self.messages_list_store.iter_next(row_iter)
        return notifications

    def on_message_checkbox_toggled(self, cell, path, model):
        """Called when the checkboxes in the notications list are clicked"""
        for column in self.columns_dict.keys():
            if self.columns_dict[column] == cell:
                column = int(column)
                row_iter = self.messages_list_store.get_iter(path)
                reversed_value = not self.messages_list_store.get_value(row_iter, column)
                self.messages_list_store.set_value(row_iter, column, reversed_value)

    def on_button_remove_notication_clicked(self, button):
        """Callback for when remove button for notifications is clicked"""
        tree, row_iter = self.messages_treeview.get_selection().get_selected()
        if row_iter:
            self.messages_list_store.remove(row_iter)

    def on_button_last_matched_reset_clicked(self, button):
        self.get_object("txt_last_matched").set_text("")

    def on_button_last_matched_now_clicked(self, button):
        self.get_object("txt_last_matched").set_text(get_current_date_in_isoformat())

    def show_rssfeed_mandatory_message(self):
        md = Gtk.MessageDialog(self.dialog, Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                               Gtk.ButtonsType.CLOSE, "You must select an RSS Feed")
        md.run()
        md.destroy()

    def on_button_cancel_clicked(self, event=None):
        self.destroy()

    def on_key_pressed(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()

    def on_button_save_subscription_clicked(self, event=None, a=None, col=None):
        if self.save_subscription_data():
            self.destroy()

    def save_subscription_data(self):
        raise NotImplementedError("Should not be called")

    def on_txt_regex_changed(self, text_field):
        """ Callback for when Enter is pressed in either of the regex fields """
        self.perform_search()

    def perform_search(self):
        raise NotImplementedError("Should not be called")

    def on_rssfeed_selected(self, combobox):
        """
        Callback from glade when rss combobox is selected.
        Gets the results for the RSS Feed
        Runs the code that handles the parsing in a thread with Twisted,
        to avoid the dialog waiting on startup.
        """
        self.method_perform_rssfeed_selection()

    def on_button_add_torrent_clicked(self, menuitem, use_settings=False):
        torrent_link = get_value_in_selected_row(self.matching_treeview,
                                                 self.matching_store, column_index=3)

        self.button_add_torrent_clicked(torrent_link, use_settings)

    def button_add_torrent_clicked(self, torrent_link, use_settings):
        raise NotImplementedError("Should not be called")

    ########################################
    # Get and set data
    ########################################

    def update_matching_feeds_store(self, rssfeeds_dict, regex_matching=False):
        """
        Updates the liststore of matching torrents.
        This updates the GUI
        """
        store = self.matching_store
        store.clear()
        for key in sorted(rssfeeds_dict.keys()):
            custom_attributes = CustomAttribute()
            if regex_matching:
                attr = {}
                if "regex_include_match" in rssfeeds_dict[key]:
                    attr["regex_include_match"] = rssfeeds_dict[key]["regex_include_match"]
                if "regex_exclude_match" in rssfeeds_dict[key]:
                    attr["regex_exclude_match"] = rssfeeds_dict[key]["regex_exclude_match"]
                custom_attributes = CustomAttribute(attributes_dict=attr)
            updated = rssfeeds_dict[key]['updated']
            store.append([rssfeeds_dict[key]['matches'], rssfeeds_dict[key]['title'],
                          updated if updated else "Not available", rssfeeds_dict[key]['link'],
                          custom_attributes, rssfeeds_dict[key]["torrent"], rssfeeds_dict[key]["magnet"], key])

    def get_subscription_data(self):
        name = self.get_object("txt_name").get_text()
        regex_include = self.get_object("txt_regex_include").get_text()
        regex_exclude = self.get_object("txt_regex_exclude").get_text()
        regex_include_case_sensitive = self.get_object("regex_include_case").get_active()
        regex_exclude_case_sensitive = self.get_object("regex_exclude_case").get_active()
        move_completed = ""
        active_string = self.move_completed_path_chooser.get_text()
        if active_string is not None:
            move_completed = active_string.strip()
        download_location = ""
        active_string = self.download_location_path_chooser.get_text()
        if active_string is not None:
            download_location = active_string.strip()
        last_match = self.get_object("txt_last_matched").get_text()
        ignore_timestamp = self.get_object("checkbutton_ignore_timestamp").get_active()

        max_download_speed = self.get_object("spinbutton_max_download_speed").get_value()
        max_upload_speed = self.get_object("spinbutton_max_upload_speed").get_value()
        max_connections = self.get_object("spinbutton_max_connections").get_value()
        max_upload_slots = self.get_object("spinbutton_max_upload_slots").get_value()

        add_torrents_paused = self.get_object("checkbox_add_torrents_in_paused_state").get_active()
        auto_managed = self.get_object("checkbutton_auto_managed").get_active()
        sequential_download = self.get_object("checkbutton_sequential_download").get_active()
        prioritize_first_last = self.get_object("checkbutton_prioritize_first_last").get_active()

        add_torrents_paused_default = self.get_object(
            "checkbox_add_torrents_in_paused_state_default").get_active()
        auto_managed_default = self.get_object("checkbutton_auto_managed_default").get_active()
        sequential_download_default = self.get_object("checkbutton_sequential_download_default").get_active()
        prioritize_first_last_default = self.get_object("checkbutton_prioritize_first_last_default").get_active()

        add_torrents_paused = GeneralSubsConf().bool_to_value(add_torrents_paused, add_torrents_paused_default)
        auto_managed = GeneralSubsConf().bool_to_value(auto_managed, auto_managed_default)
        sequential_download = GeneralSubsConf().bool_to_value(sequential_download, sequential_download_default)
        prioritize_first_last = GeneralSubsConf().bool_to_value(prioritize_first_last, prioritize_first_last_default)

        textbuffer = self.get_object("textview_custom_text").get_buffer()
        custom_text_lines = textbuffer.get_text(textbuffer.get_start_iter(), textbuffer.get_end_iter(), False)

        combobox_labels = self.get_object("combobox_labels")

        label = None
        active_label = combobox_labels.get_active_iter()
        if active_label is not None:
            label = combobox_labels.get_model().get_value(active_label, 0)

        subscription_data = {}
        subscription_data["name"] = name
        subscription_data["regex_include"] = regex_include
        subscription_data["regex_exclude"] = regex_exclude
        subscription_data["regex_include_ignorecase"] = not regex_include_case_sensitive
        subscription_data["regex_exclude_ignorecase"] = not regex_exclude_case_sensitive
        subscription_data["move_completed"] = move_completed
        subscription_data["download_location"] = download_location
        subscription_data["custom_text_lines"] = custom_text_lines
        subscription_data["rssfeed_key"] = self.get_current_rssfeed_key()
        subscription_data["last_match"] = last_match
        subscription_data["ignore_timestamp"] = ignore_timestamp

        subscription_data["max_download_speed"] = int(max_download_speed)
        subscription_data["max_upload_speed"] = int(max_upload_speed)
        subscription_data["max_connections"] = int(max_connections)
        subscription_data["max_upload_slots"] = int(max_upload_slots)

        subscription_data["add_torrents_in_paused_state"] = add_torrents_paused
        subscription_data["auto_managed"] = auto_managed
        subscription_data["sequential_download"] = sequential_download
        subscription_data["prioritize_first_last_pieces"] = prioritize_first_last
        subscription_data["label"] = label

        # Get notifications from notifications list
        subscription_data["email_notifications"] = self.get_current_notifications()
        return subscription_data

    def load_basic_fields_data(self, subscription_data):
        if subscription_data is None:
            return
        self.get_object("txt_name").set_text(subscription_data["name"])
        self.get_object("txt_regex_include").set_text(subscription_data["regex_include"])
        self.get_object("txt_regex_exclude").set_text(subscription_data["regex_exclude"])
        self.get_object("regex_include_case").set_active(
            not subscription_data["regex_include_ignorecase"])
        self.get_object("regex_exclude_case").set_active(
            not subscription_data["regex_exclude_ignorecase"])

        textbuffer = self.get_object("textview_custom_text").get_buffer()
        textbuffer.set_text(subscription_data["custom_text_lines"])

        self.get_object("spinbutton_max_download_speed").set_value(subscription_data["max_download_speed"])
        self.get_object("spinbutton_max_upload_speed").set_value(subscription_data["max_upload_speed"])
        self.get_object("spinbutton_max_connections").set_value(subscription_data["max_connections"])
        self.get_object("spinbutton_max_upload_slots").set_value(subscription_data["max_upload_slots"])

        add_paused = subscription_data["add_torrents_in_paused_state"]
        auto_managed = subscription_data["auto_managed"]
        sequential_download = subscription_data["sequential_download"]
        prioritize_first_last_pieces = subscription_data["prioritize_first_last_pieces"]

        self.get_object("checkbox_add_torrents_in_paused_state").set_active(
            add_paused == GeneralSubsConf.ENABLED)
        self.get_object("checkbutton_auto_managed").set_active(
            auto_managed == GeneralSubsConf.ENABLED)
        self.get_object("checkbutton_sequential_download").set_active(
            sequential_download == GeneralSubsConf.ENABLED)
        self.get_object("checkbutton_prioritize_first_last").set_active(
            prioritize_first_last_pieces == GeneralSubsConf.ENABLED)

        self.get_object("checkbox_add_torrents_in_paused_state_default").set_active(
            add_paused == GeneralSubsConf.DEFAULT)
        self.get_object("checkbutton_auto_managed_default").set_active(
            auto_managed == GeneralSubsConf.DEFAULT)
        self.get_object("checkbutton_sequential_download_default").set_active(
            sequential_download == GeneralSubsConf.DEFAULT)
        self.get_object("checkbutton_prioritize_first_last_default").set_active(
            prioritize_first_last_pieces == GeneralSubsConf.DEFAULT)

        self.on_general_checkbox_toggled(None)

    def get_search_settings(self):
        regex_include = self.get_object("txt_regex_include").get_text()
        regex_exclude = self.get_object("txt_regex_exclude").get_text()
        regex_include_case = self.get_object("regex_include_case").get_active()
        regex_exclude_case = self.get_object("regex_exclude_case").get_active()
        match_option_dict = {}
        match_option_dict["regex_include"] = regex_include if (len(regex_include) > 0) else None
        match_option_dict["regex_exclude"] = regex_exclude if (len(regex_exclude) > 0) else None
        match_option_dict["regex_include_ignorecase"] = not regex_include_case
        match_option_dict["regex_exclude_ignorecase"] = not regex_exclude_case
        match_option_dict["custom_text_lines"] = self.get_custom_text_lines()
        return match_option_dict

    def get_custom_text_lines(self):
        textbuffer = self.get_object("textview_custom_text").get_buffer()
        lines = []
        text = textbuffer.get_text(textbuffer.get_start_iter(), textbuffer.get_end_iter(), True)
        for line in text.splitlines():
            lines.append(line.strip())
        return lines

    def load_timestamp(self, subscription_data):
        self.get_object("txt_last_matched").set_text(subscription_data["last_match"])
        self.get_object("checkbutton_ignore_timestamp").set_active(subscription_data["ignore_timestamp"])

    def load_notifications_list_data(self, email_messages, subscription_data):
        # Load notification messages into combo
        for key in email_messages.keys():
            self.messages_combo_store.append([key, email_messages[key]["name"]])
        # Load notifications into notifications list
        # The dict keys in email_notifications are the email messages dict keys.
        for key in subscription_data["email_notifications"].keys():
            on_added = subscription_data["email_notifications"][key]["on_torrent_added"]
            on_completed = subscription_data["email_notifications"][key]["on_torrent_completed"]
            self.messages_list_store.append([key, email_messages[key]["name"],
                                             email_messages[key]["active"],
                                             on_added, on_completed])

    def set_path_chooses_data(self, config):
        if not config.get("move_completed_paths_list", None) is None:
            self.move_completed_path_chooser.add_values(config["move_completed_paths_list"])
        if not config.get("download_location_paths_list", None) is None:
            self.download_location_path_chooser.add_values(config["download_location_paths_list"])

        if self.new_subscription:
            self.move_completed_path_chooser.set_text(config["move_completed_path"])
            self.download_location_path_chooser.set_text(config["download_location"])
        else:
            self.move_completed_path_chooser.set_text(self.subscription_data["move_completed"])
            self.download_location_path_chooser.set_text(self.subscription_data["download_location"])

    def load_rssfeed_combobox_data(self, subscription_data, rssfeeds):
        rssfeed_key = "-1"
        active_index = -1
        if subscription_data:
            # If editing a subscription, set the rssfeed_key
            if self.editing:
                rssfeed_key = subscription_data["rssfeed_key"]
        # Load rssfeeds into the combobox
        count = 0
        for key in sorted(rssfeeds):
            self.rssfeeds_store.append([rssfeeds[key]["key"],
                                        rssfeeds[key]["name"],
                                        "(%s)" % rssfeeds[key]["site"]])
            if key == rssfeed_key:
                active_index = count
            count += 1
        # Set active index
        self.get_object("combobox_rssfeeds").set_active(active_index)
        # Update matching
        self.on_txt_regex_changed(None)

    def load_labels(self, labels, subscription_data):
        if self.labels is None:
            return
        current = subscription_data["label"]
        active_index = 0
        for i, label in enumerate(self.labels):
            if label == current:
                active_index = i
            self.labels_liststore.append([label])
        combobox_labels = self.get_object("combobox_labels")
        combobox_labels.set_active(active_index)


def get_viewable_result(rssfeed_parsed):
    if "summary" not in rssfeed_parsed["feed"]:
        return ""
    cleaned = rssfeed_parsed["feed"]["summary"]
    s = http.HTMLStripper()
    s.feed(cleaned)
    return s.get_data()


class DialogSubscription(DialogSubscriptionGUI):

    def __init__(self, gtkui, logger, subscription_data, rssfeeds, email_messages, cookies):
        self.gtkUI = gtkui
        self.rssfeeds = rssfeeds
        self.email_messages = email_messages
        self.rssfeeds_dict = {}
        self.subscription_data = subscription_data
        self.cookies = cookies
        self.log = logger
        self.rssfeedhandler = RSSFeedHandler(self.log)
        # This is to make testing of the GUI possible (unit tests)
        self.method_perform_rssfeed_selection = self.perform_rssfeed_selection
        super().__init__(editing=True if len(self.subscription_data.get("rssfeed_key", "")) != 0 else False,
                         new_subscription="key" not in subscription_data)

    def show(self):
        self.setup(show=True)

    def setup(self, show=False):
        """
        Called by tests where show must be False
        """
        self.setup_gui()
        if show:
            self.show_dialog()
        self.load_subscription_data()

    def button_add_torrent_clicked(self, torrent_link, use_settings):
        # Save current data to dict
        self.store_subscription_data()
        self.add_torrent(torrent_link, self.subscription_data if use_settings else None)

    def add_torrent(self, torrent_link, subscription_data):
        if torrent_link is None:
            return

        def add_torrent_callback(torrent_download):
            torrent_download = TorrentDownload(torrent_download)
            if torrent_download.success:
                return True
            if torrent_download.filedump is None:
                return

            readable_body = http.clean_html_body(torrent_download.filedump)
            textbuffer = self.get_object("textview_messages").get_buffer()
            textbuffer.set_text(readable_body)

            self.get_object("notebook_lower").set_current_page(1)

            # Quick hack to make sure the message is visible to the user.
            hpaned = self.get_object("hpaned_matching")
            max_pos = hpaned.get_property("max-position")
            hpaned.set_position(int(max_pos * 0.3))
            return False

        d = self.gtkUI.add_torrent(torrent_link, subscription_data)
        d.addCallback(add_torrent_callback)
        return d

    ##################
    # RSS Matching
    ##################

    def perform_rssfeed_selection(self):
        rssfeed_key = self.get_current_rssfeed_key()
        deferred = self.get_and_update_rssfeed_results(rssfeed_key)
        deferred.addCallback(self.update_matching_view_with_rssfeed_results)
        return deferred

    def perform_search(self):
        match_option_dict = self.get_search_settings()
        self.perform_matching_and_update_liststore(match_option_dict)
        # Insert treeview
        self.set_matching_window_child(self.treeview)

    def perform_matching_and_update_liststore(self, match_option_dict):
        """
        Updates the rssfeed_dict with matching according to
        options in match_option_dict Also updates the GUI
        """
        if not self.rssfeeds_dict and not match_option_dict["custom_text_lines"]:
            return
        try:
            matchings, message = self.rssfeedhandler.update_rssfeeds_dict_matching(self.rssfeeds_dict,
                                                                                   options=match_option_dict)
            self.update_matching_feeds_store(self.rssfeeds_dict, regex_matching=True)
            label_status = self.get_object("label_status")
            if message:
                label_status.set_text(str(message))
            label_count = self.get_object("label_torrent_count")
            label_count.set_text("Matching: %d/%d" %
                                 (len(matchings.keys()), len(self.rssfeeds_dict.keys())))
        except Exception:
            import traceback
            exc_str = traceback.format_exc()
            self.log.warn("Error when matching:" + exc_str, gtkui=True)

    def get_and_update_rssfeed_results(self, rssfeed_key):
        """
        Returns:
            Deferred:
        """
        site_cookies_dict = http.get_matching_cookies_dict(self.cookies, self.rssfeeds[rssfeed_key]["site"])
        user_agent = get_user_agent(rssfeed_data=self.rssfeeds[rssfeed_key])
        return self.get_rssfeed_parsed(self.rssfeeds[rssfeed_key],
                                       site_cookies_dict=site_cookies_dict,
                                       user_agent=user_agent)

    def get_rssfeed_parsed(self, rssfeed_data, site_cookies_dict=None, user_agent=None):
        return client.yarss2.get_rssfeed_parsed(rssfeed_data,
                                                site_cookies_dict=site_cookies_dict,
                                                user_agent=user_agent)

    def update_matching_view_with_rssfeed_results(self, rssfeeds_parsed):
        """Callback function, called when 'get_and_update_rssfeed_results'
        has finished.
        Replaces the content of the matching window.
        If valid items were retrieved, update the matching according
        to current settings.
        If no valid items, show the result as text instead.
        """
        if rssfeeds_parsed is None:
            return

        # Window has been closed in the meantime
        if not self.dialog.get_visible():
            return

        # Reset status to not display an older status
        label_status = self.get_object("label_status")
        label_text = ""
        # Bozo Exception (feedbparser error), still elements might have been successfully parsed

        if "bozo_exception" in rssfeeds_parsed:
            exception = rssfeeds_parsed["bozo_exception"]
            label_text = str(exception)
        else:
            message_text = "TTL value: %s" % (("%s min" % rssfeeds_parsed["ttl"])
                                              if rssfeeds_parsed.get("ttl", None) is not None
                                              else "Not available")
            # This can sometimes be None for some effing reason
            if label_status:
                label_text = message_text
        try:
            # label_status is sometimes None, for som effin reason
            label_status.set_text(label_text)
        except AttributeError:
            self.log.warn("label_status is None", gtkui=False)
            pass

        # Failed to retrive items. Show content as text
        if "items" not in rssfeeds_parsed:
            self.show_result_as_text(rssfeeds_parsed["raw_result"])
            return
        self.rssfeeds_dict = rssfeeds_parsed["items"]

        # Update the matching according to the current settings
        self.perform_search()

    def show_result_as_text(self, raw_rssfeed):
        """
        When failing to parse the RSS Feed, this will show the result
        in a text window with HTML tags stripped away.
        """
        result = get_viewable_result(raw_rssfeed)
        self.set_matching_result_in_textview(result)

    def save_subscription_data(self):
        if not self.store_subscription_data():
            return False
        # Call save method in gtui. Saves to core
        self.gtkUI.save_subscription(self.subscription_data)
        return True

    def store_subscription_data(self):
        """
        Get the subscription data from the GUI and store in self.subscription_data

        """
        rssfeed_key = self.get_current_rssfeed_key()
        # RSS feed is mandatory
        if not rssfeed_key:
            self.show_rssfeed_mandatory_message()
            return False

        subscription_data = self.get_subscription_data()
        self.subscription_data.update(subscription_data)
        return True

    def load_subscription_data(self):
        self.load_basic_fields_data(self.subscription_data)
        self.load_rssfeed_combobox_data(self.subscription_data, self.rssfeeds)
        self.load_notifications_list_data(self.email_messages, self.subscription_data)
        self.load_path_choosers_data()
        self.load_timestamp(self.subscription_data)
        self.get_labels_d.addCallback(self.load_labels, self.subscription_data)

    def load_path_choosers_data(self):
        self.core_keys = [
            "download_location",
            "move_completed_path",
            "move_completed_paths_list",
            "download_location_paths_list",
        ]
        client.core.get_config_values(self.core_keys).addCallback(self.set_path_chooses_data)
