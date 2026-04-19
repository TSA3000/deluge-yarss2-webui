# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2019 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#
import pytest
from twisted.internet import defer, task
from twisted.trial import unittest

import deluge.component as component
import deluge.config
from deluge.ui.client import client

import yarss2.gtk3ui.gtkui
from yarss2.gtk3ui.gtkui import GtkUI
from yarss2.tests import common as tests_common
from yarss2.util import logging

from . import test_gtkui
from .utils.log_utils import plugin_tests_logger_name

yarss2.gtk3ui.gtkui.component = test_gtkui


class DummyComponent(object):
    def add_page(self, name, widget):
        pass

    def register_hook(self, name, func):
        pass


def get(string):
    return DummyComponent()


class GtkUITestCase(unittest.TestCase):

    def setUp(self):  # NOQA
        defer.setDebugging(True)
        tests_common.set_tmp_config_dir()
        client.start_standalone()

        self.log = logging.getLogger(plugin_tests_logger_name)
        self.gtkui = GtkUI("YaRSS2")
        self.gtkui.create_ui()

    def tearDown(self):  # NOQA
        client._daemon_proxy = None
        client.__started_standalone = False

        def on_shutdown(result):
            component._ComponentRegistry.components = {}
        return component.shutdown().addCallback(on_shutdown)


@pytest.mark.label
class GtkUIWithCoreTestCase(unittest.TestCase):

    @defer.inlineCallbacks
    def setUp(self):  # NOQA
        # Must override callLater to avoid unclean twisted reactor
        clock = task.Clock()
        deluge.config.callLater = clock.callLater

        tests_common.set_tmp_config_dir()
        client.start_standalone()

        success = yield client.core.enable_plugin("Label")
        self.assertTrue(success, msg="Failed to enable Label plugin")

        self.log = logging.getLogger(plugin_tests_logger_name)
        self.gtkui = GtkUI("YaRSS2")
        self.gtkui.create_ui()

    def tearDown(self):  # NOQA
        client._daemon_proxy = None
        client.__started_standalone = False
        return component.shutdown()

    @defer.inlineCallbacks
    def test_get_labels(self, *patched_get):
        from deluge.i18n import setup_mock_translation
        setup_mock_translation()

        yield component.start()  # Necessary to avoid 'Reactor was unclean' error

        labels = yield self.gtkui.plugins_enabled_changed("Label")
        self.assertEquals([""], labels)

        # Add some labels
        client.label.add("Test-label")
        client.label.add("Test-label2")

        labels = yield self.gtkui.plugins_enabled_changed("Label")

        self.failUnlessIn("test-label", labels)
        self.failUnlessIn("test-label2", labels)
