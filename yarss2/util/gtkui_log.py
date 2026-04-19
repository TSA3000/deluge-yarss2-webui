# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2015 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

from deluge.event import DelugeEvent

from yarss2.util.common import get_current_date_in_isoformat


class GTKUILogger(object):
    """This class handles messages going to the GTKUI log message pane"""

    def __init__(self, textview):
        self.textview = textview
        self.show_log_in_gui = True

    def gtkui_log_message(self, message):
        if self.show_log_in_gui is False:
            return

        def add_msg():
            buf = self.textview.get_buffer()
            time = get_current_date_in_isoformat()
            msg_to_append = "(%s): %s" % (time, message)
            buf.insert(buf.get_end_iter(), msg_to_append + "\n")
        from gi.repository import GLib  # Do not import on top as only the client needs to have this package
        GLib.idle_add(add_msg)


class GtkUILogMessageEvent(DelugeEvent):
    """
    Emitted when a message has been written to the log.
    """
    def __init__(self, message):
        """
        :param message: the message to be logged
        """
        self._args = [message]
