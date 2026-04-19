# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2015 bendikro bro.devel+yarss2@gmail.com
#
# Based on work by:
# Copyright (C) 2009 Camillo Dell'mour <cdellmour@gmail.com>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#
from twisted.internet import defer

import deluge.component as component
from deluge.plugins.pluginbase import Gtk3PluginBase
from deluge.ui.client import client

from yarss2 import yarss_config
from yarss2.util import logging
from yarss2.util.common import get_resource, get_value_in_selected_row
from yarss2.util.gtkui_log import GTKUILogger
from yarss2.util.http import encode_cookie_values

from .common import Gtk, popup_gtk_menu
from .dialog_cookie import DialogCookie
from .dialog_email_message import DialogEmailMessage
from .dialog_rssfeed import DialogRSSFeed
from .dialog_subscription import DialogSubscription


class GtkUI(Gtk3PluginBase):

    def enable(self):
        self.create_ui()
        self.on_show_prefs()  # Necessary for the first time when the plugin is installed
        client.register_event_handler("YARSSConfigChangedEvent", self.cb_on_config_changed_event)
        client.register_event_handler("GtkUILogMessageEvent", self.cb_on_log_message_arrived_event)
        client.register_event_handler("PluginEnabledEvent", self.plugins_enabled_changed)
        client.register_event_handler("PluginDisabledEvent", self.plugins_enabled_changed)
        self.plugins_enabled_changed("Label")

    def disable(self):
        component.get("Preferences").remove_page("YaRSS2")
        component.get("PluginManager").deregister_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").deregister_hook("on_show_prefs", self.on_show_prefs)

    def create_ui(self):
        self.glade = Gtk.Builder.new_from_file(get_resource("yarss_main.ui"))
        self.glade.connect_signals({
            "on_button_add_subscription_clicked": self.on_button_add_subscription_clicked,
            "on_button_delete_subscription_clicked": self.on_button_delete_subscription_clicked,
            "on_button_edit_subscription_clicked": self.on_button_edit_subscription_clicked,

            "on_button_add_rssfeed_clicked": self.on_button_add_rssfeed_clicked,
            "on_button_delete_rssfeed_clicked": self.on_button_delete_rssfeed_clicked,
            "on_button_edit_rssfeed_clicked": self.on_button_edit_rssfeed_clicked,

            "on_button_add_cookie_clicked": self.on_button_add_cookie_clicked,
            "on_button_edit_cookie_clicked": self.on_button_edit_cookie_clicked,
            "on_button_delete_cookie_clicked": self.on_button_delete_cookie_clicked,

            "on_button_add_message_clicked": self.on_button_add_message_clicked,
            "on_button_edit_message_clicked": self.on_button_edit_message_clicked,
            "on_button_delete_message_clicked": self.on_button_delete_message_clicked,

            "on_checkbox_email_authentication_toggled": self.on_checkbox_email_authentication_toggled,
            "on_checkbutton_show_log_messages_gui_toggled": self.on_checkbutton_show_log_messages_gui_toggled,
        })

        component.get("Preferences").add_page("YaRSS2", self.glade.get_object("notebook_main"))
        component.get("PluginManager").register_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").register_hook("on_show_prefs", self.on_show_prefs)
        self.gtkui_log = GTKUILogger(self.glade.get_object('textview_log'))
        self.log = logging.getLogger(__name__, gtkui_logger=self.gtkui_log)

        self.subscriptions = {}
        self.rssfeeds = {}

        self.selected_path_subscriptions = None
        self.selected_path_rssfeeds = None
        self.selected_path_email_message = None
        self.selected_path_cookies = None

        self.label_enabled = False

        # key, enabled, name, site, download_location
        self.subscriptions_store = Gtk.ListStore(str, bool, str, str, str, str, str)

        # key, active, name, site, Update interval, Last update, subscripions, URL
        self.rssfeeds_store = Gtk.ListStore(str, bool, str, str, str, str, str, str)

        # key, active, site, value
        self.cookies_store = Gtk.ListStore(str, bool, str, str)

        # key, active, name, to-address, subject, message-content
        self.email_messages_store = Gtk.ListStore(str, bool, str, str, str, str)

        self.create_subscription_pane()
        self.create_rssfeeds_pane()
        self.create_cookies_pane()
        self.create_email_messages_pane()

##############################
# Save data and delete data from core
###############################

    def save_subscription(self, subscription_data, subscription_key=None, delete=False):
        """Called by the RSSFeed Dialog"""
        self.selected_path_subscriptions = self.get_selection_path(self.subscriptions_treeview)
        client.yarss2.save_subscription(dict_key=subscription_key, subscription_data=subscription_data,
                                        delete=delete).addCallback(self.cb_get_config)

    def save_rssfeed(self, rssfeed_data, rssfeed_key=None, delete=False):
        """Called by the RSSFeed Dialog"""
        self.selected_path_rssfeeds = self.get_selection_path(self.rssfeeds_treeview)
        client.yarss2.save_rssfeed(dict_key=rssfeed_key, rssfeed_data=rssfeed_data,
                                   delete=delete).addCallback(self.cb_get_config)

    def save_email_message(self, message_data, email_message_key=None, delete=False):
        self.selected_path_email_message = self.get_selection_path(self.email_messages_treeview)
        client.yarss2.save_email_message(dict_key=email_message_key, message_data=message_data,
                                         delete=delete).addCallback(self.cb_get_config)

    def save_cookie(self, cookie_data, cookie_key=None, delete=False):
        self.selected_path_cookies = self.get_selection_path(self.cookies_treeview)
        client.yarss2.save_cookie(dict_key=cookie_key, cookie_data=cookie_data,
                                  delete=delete).addCallback(self.cb_get_config)

    def save_email_config(self, email_config):
        client.yarss2.save_email_configurations(email_config)

    def save_general_config(self, config):
        client.yarss2.save_general_config(config)

    def add_torrent(self, torrent_link, subscription_data):
        torrent_info = {"link": torrent_link, "subscription_data": subscription_data}
        if subscription_data is not None:
            torrent_info["rssfeed_key"] = subscription_data["rssfeed_key"]
        return client.yarss2.add_torrent(torrent_info)

##############################
# Update config and lists data
###############################

    def on_apply_prefs(self):
        """Called when the 'Apply' button is pressed"""
        self.save_configuration_data()

    def save_configuration_data(self):
        # Save:
        # Settings -> Email Notifications -> Enable/Disable email notifcations
        # Settings -> Email configuration -> all fields
        # Settings -> Default values -> All fields

        send_emails = self.glade.get_object("checkbutton_send_email_on_torrent_events").get_active()
        from_addr = self.glade.get_object("txt_email_from").get_text()
        smtp_server = self.glade.get_object("txt_email_server").get_text()
        smtp_port = self.glade.get_object("txt_email_port").get_text()
        smtp_username = self.glade.get_object("txt_email_username").get_text()
        smtp_password = self.glade.get_object("txt_email_password").get_text()
        enable_auth = self.glade.get_object("checkbox_email_enable_authentication").get_active()

        default_to_address = self.glade.get_object("txt_default_to_address").get_text()
        default_subject = self.glade.get_object("txt_default_subject").get_text()
        textbuffer = self.glade.get_object("textview_default_message").get_buffer()
        default_message = textbuffer.get_text(textbuffer.get_start_iter(), textbuffer.get_end_iter(), True)

        self.email_config["send_email_on_torrent_events"] = send_emails
        self.email_config["from_address"] = from_addr
        self.email_config["smtp_server"] = smtp_server
        self.email_config["smtp_port"] = smtp_port
        self.email_config["smtp_authentication"] = enable_auth
        self.email_config["smtp_username"] = smtp_username
        self.email_config["smtp_password"] = smtp_password
        self.email_config["default_email_to_address"] = default_to_address
        self.email_config["default_email_subject"] = default_subject
        self.email_config["default_email_message"] = default_message
        self.save_email_config(self.email_config)
        self.save_general_config(self.general_config)

    def on_show_prefs(self):
        """Called when showing preferences window"""
        client.yarss2.get_config().addCallback(self.cb_get_config)

    def cb_on_config_changed_event(self, config):
        """Callback function called on YARSSConfigChangedEvent events"""
        # Tried to fix error where glade.get_object("label_status") in dialog_subscription returns None. (Why??)
        # DeferToThread actually works, but it seems to add a new error, where Deluge crashes, probably
        # caused by the GUI being updated in another thread than the main thread.
        # from twisted.internet import threads
        # d = threads.deferToThread(self.cb_get_config, config)
        self.cb_get_config(config)

    def cb_on_log_message_arrived_event(self, message):
        """Callback function called on GtkUILogMessageEvent events"""
        self.gtkui_log.gtkui_log_message(message)

    def on_checkbutton_show_log_messages_gui_toggled(self, widget):
        show_log_in_gui = self.glade.get_object("checkbutton_show_log_messages_gui").get_active()
        self.general_config["show_log_in_gui"] = show_log_in_gui
        self.gtkui_log.show_log_in_gui = show_log_in_gui
        self.save_general_config(self.general_config)

    def cb_get_config(self, config):
        """Callback function called after saving data to core"""
        if config is None:
            self.log.error("An error has occured. Cannot load data from config")
        else:
            self.update_data_from_config(config)

    def update_data_from_config(self, config):
        self.subscriptions = config.get('subscriptions', {})
        self.rssfeeds = config.get('rssfeeds', {})
        self.cookies = config.get('cookies', {})
        self.email_messages = config.get('email_messages', {})
        self.email_config = config.get('email_configurations', {})
        self.default_values = config.get('default_values', {})
        self.general_config = config.get('general', {})

        # When connecting to a second host, the glade object returns None for all the fields,
        # so reload the glade file here to avoid this problem.
        if self.glade.get_object("textview_default_message") is None:
            self.glade = Gtk.Builder.new_from_file(get_resource("yarss_main.ui"))

        # Update GUI
        self.update_subscription_list(self.subscriptions_store)
        self.update_rssfeeds_list(self.rssfeeds_store)
        self.update_cookies_list(self.cookies_store)
        self.update_email_messages_list(self.email_messages_store)

        # Set selection for each treeview
        if self.selected_path_subscriptions and self.subscriptions_treeview.get_selection():
            self.subscriptions_treeview.get_selection().select_path(self.selected_path_subscriptions)

        if self.selected_path_rssfeeds and self.rssfeeds_treeview.get_selection():
            self.rssfeeds_treeview.get_selection().select_path(self.selected_path_rssfeeds)

        if self.selected_path_email_message and self.email_messages_treeview.get_selection():
            self.email_messages_treeview.get_selection().select_path(self.selected_path_email_message)

        if self.selected_path_cookies and self.cookies_treeview.get_selection():
            self.cookies_treeview.get_selection().select_path(self.selected_path_cookies)

        # Email configurations
        send_email_checkbox = self.glade.get_object("checkbutton_send_email_on_torrent_events")
        from_addr = self.glade.get_object("txt_email_from")
        smtp_server = self.glade.get_object("txt_email_server")
        smtp_port = self.glade.get_object("txt_email_port")
        smtp_username = self.glade.get_object("txt_email_username")
        smtp_password = self.glade.get_object("txt_email_password")
        enable_auth = self.glade.get_object("checkbox_email_enable_authentication")

        default_to_address = self.glade.get_object("txt_default_to_address")
        default_subject = self.glade.get_object("txt_default_subject")
        default_message = self.glade.get_object("textview_default_message")

        default_message = default_message.get_buffer()
        from_addr.set_text(self.email_config["from_address"])
        smtp_server.set_text(self.email_config["smtp_server"])
        smtp_port.set_text(self.email_config["smtp_port"])

        enable_auth.set_active(self.email_config["smtp_authentication"])
        smtp_username.set_text(self.email_config["smtp_username"])
        smtp_password.set_text(self.email_config["smtp_password"])

        default_to_address.set_text(self.email_config["default_email_to_address"])
        default_subject.set_text(self.email_config["default_email_subject"])
        default_message.set_text(self.email_config["default_email_message"])

        # Must be last, since it will cause callback on
        # method on_checkbutton_send_email_on_torrent_events_toggled
        send_email_checkbox.set_active(self.email_config["send_email_on_torrent_events"])

        show_log_in_gui = self.general_config.get('show_log_in_gui', True)
        self.gtkui_log.show_log_in_gui = show_log_in_gui
        self.glade.get_object("checkbutton_show_log_messages_gui").set_active(show_log_in_gui)

    def update_subscription_list(self, subscriptions_store):
        subscriptions_store.clear()

        for key in self.subscriptions.keys():
            rssfeed_key = self.subscriptions[key]["rssfeed_key"]
            subscriptions_store.append([self.subscriptions[key]["key"],
                                        self.subscriptions[key]["active"],
                                        self.subscriptions[key]["name"],
                                        self.rssfeeds[rssfeed_key]["name"],
                                        self.rssfeeds[rssfeed_key]["site"],
                                        self.subscriptions[key]["last_match"],
                                        self.subscriptions[key]["move_completed"]])

    def update_rssfeeds_list(self, rssfeeds_store):
        rssfeeds_store.clear()
        active_subscriptions = self.get_subscription_count_for_feeds()
        for key in self.rssfeeds.keys():
            active_subs = "0"
            if key in active_subscriptions:
                tmp = active_subscriptions[key]
                active_subs = "%s (%s)" % (tmp[0], tmp[1])
            rssfeeds_store.append([self.rssfeeds[key]["key"],
                                   self.rssfeeds[key]["active"],
                                   self.rssfeeds[key]["name"],
                                   self.rssfeeds[key]["site"],
                                   str(self.rssfeeds[key]["update_interval"]),
                                   self.rssfeeds[key]["last_update"],
                                   active_subs,
                                   self.rssfeeds[key]["url"]])

    def update_cookies_list(self, cookies_store):
        cookies_store.clear()
        # key, active, site, value
        for key in self.cookies.keys():
            cookies_store.append([key, self.cookies[key]["active"],
                                  self.cookies[key]["site"],
                                  encode_cookie_values(self.cookies[key]["value"])])

    def update_email_messages_list(self, store):
        store.clear()
        # key, active, name, to-address, subject, message-content
        for key in self.email_messages.keys():
            store.append([key, self.email_messages[key]["active"],
                          self.email_messages[key]["name"],
                          self.email_messages[key]["to_address"],
                          self.email_messages[key]["subject"],
                          self.email_messages[key]["message"],
                          ])

    def get_subscription_count_for_feeds(self):
        """Creates the subscription count for each RSS Feed shown in the RSS Feeds list"""
        result = {}
        for key in self.rssfeeds.keys():
            result[key] = [0, 0]
        for key in self.subscriptions.keys():
            rssfeed_key = self.subscriptions[key]["rssfeed_key"]
            index = 0 if self.subscriptions[key]["active"] is True else 1
            result[rssfeed_key][index] += 1
        return result

    def get_selection_path(self, treeview):
        """Returns the (first) selected path from a treeview"""
        tree_selection = treeview.get_selection()
        model, tree_paths = tree_selection.get_selected_rows()
        if len(tree_paths) > 0:
            return tree_paths[0]
        return None

    def get_labels(self):
        if self.label_enabled is False:
            return defer.succeed(None)

        def on_labels(labels):
            self.log.debug("Got Labels: %s" % str(labels))
            labels = list(labels)
            labels.insert(0, "")
            return defer.succeed(labels)
        d = client.label.get_labels()
        d.addCallback(on_labels)
        return d

    def plugins_enabled_changed(self, name):
        if name == "Label":
            d = client.core.get_enabled_plugins()
            d.addCallback(self.on_get_enabled_plugins)
            return d
        return defer.succeed(None)

    def on_get_enabled_plugins(self, result):
        if "Label" in result:
            self.label_enabled = True
            return self.get_labels()
        self.label_enabled = False
        return defer.succeed(None)

    ###########################
    # Create Subscription list
    ###########################

    def on_tooltip_subscription(self, widget, x, y, keyboard_tip, tooltip):
        x, y = self.subscriptions_treeview.convert_widget_to_bin_window_coords(x, y)
        if widget.get_path_at_pos(x, y) is None:
            return False
        path, tree_column, t, r = widget.get_path_at_pos(x, y)
        if tree_column.get_title() == "Active":
            tooltip.set_markup("<b>Double click to toggle</b>")
        elif tree_column.get_title() == "Last Matched":
            tooltip.set_markup("<b>The publish time of the last torrent that was added by this subscription.</b>")
        else:
            return False
        widget.set_tooltip_cell(tooltip, path, None, None)
        return True

    def create_subscription_pane(self):
        subscriptions_box = self.glade.get_object("subscriptions_box")
        subscriptions_window = Gtk.ScrolledWindow()
        subscriptions_window.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        subscriptions_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        subscriptions_box.pack_start(subscriptions_window, True, True, 0)

        self.subscriptions_treeview = Gtk.TreeView(model=self.subscriptions_store)
        self.subscriptions_treeview.get_selection().connect("changed",
                                                            self.on_subscription_listitem_activated)
        self.subscriptions_treeview.connect("row-activated", self.on_button_edit_subscription_clicked)
        self.subscriptions_treeview.connect('button-press-event',
                                            self.on_subscription_list_button_press_event)

        self.subscriptions_treeview.connect('query-tooltip', self.on_tooltip_subscription)
        self.subscriptions_treeview.set_has_tooltip(True)

        self.create_subscription_columns(self.subscriptions_treeview)

        subscriptions_window.add(self.subscriptions_treeview)
        subscriptions_window.show_all()

    def create_subscription_columns(self, subscriptions_treeview):
        renderertoggle = Gtk.CellRendererToggle()
        column = Gtk.TreeViewColumn("Active", renderertoggle, activatable=1, active=1)
        column.set_sort_column_id(1)
        subscriptions_treeview.append_column(column)

        renderertext = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Name", renderertext, text=2)
        column.set_sort_column_id(2)
        subscriptions_treeview.append_column(column)

        renderertext = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Feed name", renderertext, text=3)
        column.set_sort_column_id(3)
        subscriptions_treeview.append_column(column)

        renderertext = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Site", renderertext, text=4)
        column.set_sort_column_id(4)
        subscriptions_treeview.append_column(column)

        renderertext = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Last Matched", renderertext, text=5)
        column.set_sort_column_id(5)
        subscriptions_treeview.append_column(column)

        renderertext = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Move Completed", renderertext, text=6)
        column.set_sort_column_id(6)
        subscriptions_treeview.append_column(column)

        self.subscription_popup_menu = Gtk.Menu()

        menuitem = Gtk.MenuItem(label="Run this subscription")
        self.subscription_popup_menu.append(menuitem)
        menuitem.connect("activate", self.on_button_run_subscription_clicked)

        menuitem = Gtk.MenuItem(label="Reset last matched timestamp")
        self.subscription_popup_menu.append(menuitem)
        menuitem.connect("activate", self.on_button_reset_last_matched)

    def on_button_run_subscription_clicked(self, menuitem):
        key = get_value_in_selected_row(self.subscriptions_treeview, self.subscriptions_store)
        if key:
            client.yarss2.initiate_rssfeed_update(None, subscription_key=key)

    def on_button_reset_last_matched(self, menuitem):
        key = get_value_in_selected_row(self.subscriptions_treeview, self.subscriptions_store)
        if key:
            self.subscriptions[key]["last_match"] = ""
            self.save_subscription(self.subscriptions[key])

    def on_subscription_list_button_press_event(self, treeview, event):
        """Shows popup on selected row when right clicking"""
        return popup_gtk_menu(self.subscription_popup_menu, treeview, event)

    #########################
    # Create RSS Feeds list
    #########################

    def on_tooltip_rssfeed(self, widget, x, y, keyboard_tip, tooltip):
        x, y = self.rssfeeds_treeview.convert_widget_to_bin_window_coords(x, y)
        if widget.get_path_at_pos(x, y) is None:
            return False
        path, tree_column, t, r = widget.get_path_at_pos(x, y)
        if tree_column.get_title() == "Active":
            tooltip.set_markup("<b>Double click to toggle</b>")
        elif tree_column.get_title() == "Subscriptions":
            tooltip.set_markup("<b>Active (Not active)</b>")
        elif tree_column.get_title() == "Last Update":
            tooltip.set_markup("<b>When this RSS Feed was last checked</b>")
        elif tree_column.get_title() == "Update Interval":
            tooltip.set_markup("<b>The time in minutes between each time this RSS Feed is checked</b>")
        else:
            return False
        widget.set_tooltip_cell(tooltip, path, None, None)
        return True

    def create_rssfeeds_pane(self):
        rssfeeds_box = self.glade.get_object("rssfeeds_box")

        self.rssfeeds_treeview = Gtk.TreeView(model=self.rssfeeds_store)
        self.rssfeeds_treeview.connect("row-activated", self.on_button_edit_rssfeed_clicked)
        self.rssfeeds_treeview.get_selection().connect("changed", self.on_rssfeed_listitem_activated)

        self.rssfeeds_treeview.connect('query-tooltip', self.on_tooltip_rssfeed)
        self.rssfeeds_treeview.set_has_tooltip(True)

        self.create_feeds_columns(self.rssfeeds_treeview)
        rssfeeds_box.add(self.rssfeeds_treeview)
        rssfeeds_box.show_all()

    def create_feeds_columns(self, treeview):
        # key, active, name, site, Update interval, Last update, subscriptions, URL

        renderertoggle = Gtk.CellRendererToggle()
        column = Gtk.TreeViewColumn("Active", renderertoggle, activatable=1, active=1)
        column.set_sort_column_id(1)
        treeview.append_column(column)

        renderertext = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Feed Name", renderertext, text=2)
        column.set_sort_column_id(2)
        treeview.append_column(column)

        renderertext = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Site", renderertext, text=3)
        column.set_sort_column_id(3)
        treeview.append_column(column)

        renderertext = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Update Interval", renderertext, text=4)
        column.set_sort_column_id(4)
        treeview.append_column(column)

        renderertext = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Last Update", renderertext, text=5)
        column.set_sort_column_id(5)
        treeview.append_column(column)

        renderertext = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Subscriptions", renderertext, text=6)
        column.set_sort_column_id(6)
        treeview.append_column(column)

        renderertext = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("URL", renderertext, text=7)
        column.set_sort_column_id(7)
        treeview.append_column(column)

#########################
# Create Messages list
#########################

    def create_email_messages_pane(self):
        viewport = self.glade.get_object("viewport_email_messages_list")
        self.email_messages_treeview = Gtk.TreeView(model=self.email_messages_store)
        self.email_messages_treeview.connect("row-activated", self.on_button_edit_message_clicked)
        self.email_messages_treeview.get_selection().connect("changed", self.on_notification_list_listitem_activated)
        self.email_messages_treeview.connect('button-press-event',
                                             self.on_notification_list_button_press_event)
        self.create_messages_columns(self.email_messages_treeview)
        viewport.add(self.email_messages_treeview)
        viewport.show_all()

    def create_messages_columns(self, treeview):
        # Store: key, active, name, to-address, subject, message-content
        renderertoggle = Gtk.CellRendererToggle()
        column = Gtk.TreeViewColumn("Active", renderertoggle, activatable=1, active=1)
        column.set_sort_column_id(1)
        treeview.append_column(column)
        tt = Gtk.Tooltip()
        tt.set_text('Double-click to toggle')
        treeview.set_tooltip_cell(tt, None, None, renderertoggle)

        renderertext = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Name", renderertext, text=2)
        column.set_sort_column_id(2)
        treeview.append_column(column)

        renderertext = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("To address", renderertext, text=3)
        column.set_sort_column_id(3)
        treeview.append_column(column)

        renderertext = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Subject", renderertext, text=4)
        column.set_sort_column_id(4)
        treeview.append_column(column)

        renderertext = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Message", renderertext, text=5)
        column.set_sort_column_id(5)
        treeview.append_column(column)

        self.test_email_send_menu = Gtk.Menu()
        menuitem = Gtk.MenuItem(label="Send test email now!")
        self.test_email_send_menu.append(menuitem)
        menuitem.connect("activate", self.on_button_send_email_clicked)

    def on_button_send_email_clicked(self, menuitem):
        key = get_value_in_selected_row(self.email_messages_treeview, self.email_messages_store)

        def test_email_callback(return_value):
            if return_value:
                self.log.warn("Test email successfully sent!")
            else:
                self.log.warn("Failed to send test email!")
        # Send email from daemon
        client.yarss2.send_test_email(key).addCallback(test_email_callback)

    def on_notification_list_button_press_event(self, treeview, event):
        """Shows popup on selected row"""
        return popup_gtk_menu(self.test_email_send_menu, treeview, event)

#########################
# Create Cookies list
#########################

    def create_cookies_pane(self):
        viewport = self.glade.get_object("viewport_cookies_list")
        self.cookies_treeview = Gtk.TreeView(model=self.cookies_store)
        self.cookies_treeview.connect("row-activated", self.on_button_edit_cookie_clicked)
        self.cookies_treeview.get_selection().connect("changed", self.on_cookies_listitem_activated)
        self.create_cookies_columns(self.cookies_treeview)
        viewport.add(self.cookies_treeview)
        viewport.show_all()

        # Setup popop in cookies list to copy text to clipboard
        self.cookie_list_popup_menu = Gtk.Menu()
        menuitem_copy_cookie = Gtk.MenuItem(label="Copy cookie to clipboard")
        menuitem_copy_cookie.connect("activate", self.on_button_copy_cookie_to_clipboard)
        self.cookie_list_popup_menu.append(menuitem_copy_cookie)
        self.cookies_treeview.connect('button-press-event', self.handle_mouse_right_click_popup,
                                      self.cookie_list_popup_menu)

    def on_button_copy_cookie_to_clipboard(self, menuitem):
        cookie = self.get_value_in_selected_row(self.cookies_treeview,
                                                self.cookies_store,
                                                column_index=3)
        if cookie is not None:
            Gtk.clipboard_get().set_text(cookie)

    def get_value_in_selected_row(self, treeview, store, column_index=0):
        """Helper to get the value at index 'index_column' of the selected element
        in the given treeview.
        return None of no item is selected.
        """
        tree, tree_id = treeview.get_selection().get_selected()
        if tree_id:
            value = store.get_value(tree_id, column_index)
            return value
        return None

    def handle_mouse_right_click_popup(self, treeview, event, callback_data=None):
        """Shows popup on selected row when right clicking"""
        if event.button == 3:
            if callback_data is None:
                return False
            popupmenu_single_selection = callback_data
            popupmenu_multi_selection = None
            if type(callback_data) is tuple:
                popupmenu_single_selection, popupmenu_multi_selection = callback_data
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            model = treeview.get_model()
            it = model.get_iter(pthinfo[0])
            link = model.get_value(it, 0)
            if link is None:
                return False
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                # Only show popup when right clicking a selected file
                if not treeview.get_selection().iter_is_selected(it):
                    return True
                if popupmenu_multi_selection is not None and treeview.get_selection().count_selected_rows() > 1:
                    popupmenu_multi_selection.popup(None, None, None, event.button, time, data=path)
                    popupmenu_multi_selection.show_all()
                else:
                    popupmenu_single_selection.popup(None, None, None, event.button, time, data=path)
                    popupmenu_single_selection.show_all()
            return True

    def create_cookies_columns(self, treeview):
        # store: key, active, site, value
        renderertoggle = Gtk.CellRendererToggle()
        column = Gtk.TreeViewColumn("Active", renderertoggle, activatable=1, active=1)
        column.set_sort_column_id(1)
        treeview.append_column(column)
        tt = Gtk.Tooltip()
        tt.set_text('Double-click to toggle')
        treeview.set_tooltip_cell(tt, None, None, renderertoggle)

        renderertext = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Site", renderertext, text=2)
        column.set_sort_column_id(2)
        treeview.append_column(column)
        tt2 = Gtk.Tooltip()
        tt2.set_text('Double-click to edit')
        treeview.set_has_tooltip(True)

        renderertext = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Value", renderertext, text=3)
        column.set_sort_column_id(3)
        treeview.append_column(column)

########################################################
# CALLBACK FUNCTIONS from Glade GUI
########################################################

#############################
# SUBSCRIPTION callbacks
#############################

    def on_button_add_subscription_clicked(self, event=None, a=None, col=None):
        # Check if any RSS Feeds exists, if not, show popup
        if len(self.rssfeeds.keys()) == 0:
            md = Gtk.MessageDialog(component.get("Preferences").pref_dialog,
                                   Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                   Gtk.ButtonsType.CLOSE,
                                   "You need to add a RSS Feed before creating subscriptions!")
            md.run()
            md.destroy()
            return

        fresh_subscription_config = yarss_config.get_fresh_subscription_config()
        subscription_dialog = DialogSubscription(self,
                                                 self.log,
                                                 fresh_subscription_config,
                                                 self.rssfeeds,
                                                 self.email_messages,
                                                 self.cookies)
        subscription_dialog.show()

    def get_move_completed_list(self):
        values = []
        for key in self.subscriptions.keys():
            value = self.subscriptions[key]["move_completed"].strip()
            if len(value) > 0 and value not in values:
                values.append(value)
        return values

    def get_download_location_list(self):
        values = []
        for key in self.subscriptions.keys():
            value = self.subscriptions[key]["download_location"].strip()
            if len(value) > 0 and value not in values:
                values.append(value)
        return values

    def on_button_delete_subscription_clicked(self, event=None, a=None, col=None):
        key = get_value_in_selected_row(self.subscriptions_treeview, self.subscriptions_store)
        if key:
            self.save_subscription(None, subscription_key=key, delete=True)

    def on_button_edit_subscription_clicked(self, event=None, a=None, col=None):
        key = get_value_in_selected_row(self.subscriptions_treeview, self.subscriptions_store)
        if key:
            if col and col.get_title() == 'Active':
                self.subscriptions[key]["active"] = not self.subscriptions[key]["active"]
                self.save_subscription(self.subscriptions[key])
            else:
                edit_subscription_dialog = DialogSubscription(self,
                                                              self.log,
                                                              self.subscriptions[key],
                                                              self.rssfeeds,
                                                              self.email_messages,
                                                              self.cookies)
                edit_subscription_dialog.show()

    def on_subscription_listitem_activated(self, treeview):
        tree, tree_id = self.subscriptions_treeview.get_selection().get_selected()
        if tree_id:
            self.glade.get_object('button_edit_subscription').set_sensitive(True)
            self.glade.get_object('button_delete_subscription').set_sensitive(True)
        else:
            self.glade.get_object('button_edit_subscription').set_sensitive(False)
            self.glade.get_object('button_delete_subscription').set_sensitive(False)

#############################
# RSS Feed callbacks
#############################

    def on_button_add_rssfeed_clicked(self, event=None, a=None, col=None):
        # Get fresh config
        fresh_subscription_config = yarss_config.get_fresh_rssfeed_config(obey_ttl=True)
        rssfeed_dialog = DialogRSSFeed(self, fresh_subscription_config)
        rssfeed_dialog.show()

    def on_button_delete_rssfeed_clicked(self, event=None, a=None, col=None):
        key = get_value_in_selected_row(self.rssfeeds_treeview, self.rssfeeds_store)
        if not key:
            return
        # Check that this rss feed has no subscriptions
        feed_subscriptions = self.get_subscription_count_for_feeds()

        # Any registered subscriptions?
        if sum(feed_subscriptions[key]) > 0:
            md = Gtk.MessageDialog(component.get("Preferences").pref_dialog,
                                   Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                   Gtk.ButtonsType.CLOSE,
                                   "This RSS Feed have subscriptions registered. Delete subscriptions first!")
            md.run()
            md.destroy()
            return
        else:
            self.save_rssfeed(None, rssfeed_key=key, delete=True)

    def on_button_edit_rssfeed_clicked(self, event=None, a=None, col=None):
        key = get_value_in_selected_row(self.rssfeeds_treeview, self.rssfeeds_store)
        if key:
            if col and col.get_title() == 'Active':
                # Check if dummy
                if key == yarss_config.DUMMY_RSSFEED_KEY:
                    return
                # Save to config
                self.rssfeeds[key]["active"] = not self.rssfeeds[key]["active"]
                self.save_rssfeed(self.rssfeeds[key])
            else:
                edit_rssfeed_dialog = DialogRSSFeed(self, self.rssfeeds[key])
                edit_rssfeed_dialog.show()

    def on_rssfeed_listitem_activated(self, treeview):
        tree, tree_id = self.rssfeeds_treeview.get_selection().get_selected()
        if tree_id:
            self.glade.get_object('button_edit_rssfeed').set_sensitive(True)
            self.glade.get_object('button_delete_rssfeed').set_sensitive(True)
        else:
            self.glade.get_object('button_edit_rssfeed').set_sensitive(False)
            self.glade.get_object('button_delete_rssfeed').set_sensitive(False)

    #############################
    # EMAIL MESSAGE callbacks
    #############################

    def on_button_add_message_clicked(self, button):
        fresh_message_config = yarss_config.get_fresh_message_config()
        fresh_message_config["to_address"] = self.email_config["default_email_to_address"]
        fresh_message_config["subject"] = self.email_config["default_email_subject"]
        fresh_message_config["message"] = self.email_config["default_email_message"]

        dialog = DialogEmailMessage(self, fresh_message_config)
        dialog.show()

    def on_button_edit_message_clicked(self, event=None, a=None, col=None):
        key = get_value_in_selected_row(self.email_messages_treeview, self.email_messages_store)
        if key:
            if col and col.get_title() == 'Active':
                # Save to config
                self.email_messages[key]["active"] = not self.email_messages[key]["active"]
                self.save_email_message(self.email_messages[key])
            else:
                edit_message_dialog = DialogEmailMessage(self, self.email_messages[key])
                edit_message_dialog.show()

    def on_button_delete_message_clicked(self, button):
        message_key = get_value_in_selected_row(self.email_messages_treeview, self.email_messages_store)
        if not message_key:
            return
        # Check that this message is not used by any subscriptions
        subscriptions_with_notification = []
        # Go through subscriptions and find those with this notification
        for key in self.subscriptions.keys():
            if message_key in self.subscriptions[key]["email_notifications"].keys():
                subscriptions_with_notification.append(self.subscriptions[key]["name"])
        # Any subscriptions that use this message?
        if subscriptions_with_notification:
            subscription_titles = ''.join(["* %s\n" % title for title in subscriptions_with_notification])
            md = Gtk.MessageDialog(component.get("Preferences").pref_dialog,
                                   Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                   Gtk.ButtonsType.CLOSE)
            md.set_markup("This Email Message is used by the following subscriptions:\n<b>%s</b>"
                          "You must first remove the notication from the subscriptions "
                          "before deleting the email message!" % subscription_titles)
            md.run()
            md.destroy()
            return
        # Delete from core config
        self.save_email_message(None, email_message_key=message_key, delete=True)

    def on_checkbox_email_authentication_toggled(self, button):
        auth_enable = self.glade.get_object("checkbox_email_enable_authentication")
        self.glade.get_object("txt_email_username").set_sensitive(auth_enable.get_active())
        self.glade.get_object("txt_email_password").set_sensitive(auth_enable.get_active())

    def on_notification_list_listitem_activated(self, treeview):
        tree, tree_id = self.email_messages_treeview.get_selection().get_selected()
        if tree_id:
            self.glade.get_object('button_edit_message').set_sensitive(True)
            self.glade.get_object('button_delete_message').set_sensitive(True)
        else:
            self.glade.get_object('button_edit_message').set_sensitive(False)
            self.glade.get_object('button_delete_message').set_sensitive(False)

    ##############################
    # COOKIE callbacks
    ##############################

    def on_button_add_cookie_clicked(self, button):
        fresh_subscription_config = yarss_config.get_fresh_cookie_config()
        dialog = DialogCookie(self, fresh_subscription_config)
        dialog.show()

    def on_button_edit_cookie_clicked(self, event=None, a=None, col=None):
        key = get_value_in_selected_row(self.cookies_treeview, self.cookies_store)
        if key:
            if col and col.get_title() == 'Active':
                # Save to config
                self.cookies[key]["active"] = not self.cookies[key]["active"]
                self.save_cookie(self.cookies[key])
            else:
                dialog_cookie = DialogCookie(self, self.cookies[key])
                dialog_cookie.show()

    def on_button_delete_cookie_clicked(self, button):
        key = get_value_in_selected_row(self.cookies_treeview, self.cookies_store)
        if key:
            # Delete from core config
            self.save_cookie(None, cookie_key=key, delete=True)

    def on_cookies_listitem_activated(self, treeview):
        tree, tree_id = self.cookies_treeview.get_selection().get_selected()
        if tree_id:
            self.glade.get_object('button_edit_cookie').set_sensitive(True)
            self.glade.get_object('button_delete_cookie').set_sensitive(True)
        else:
            self.glade.get_object('button_edit_cookie').set_sensitive(False)
            self.glade.get_object('button_delete_cookie').set_sensitive(False)
