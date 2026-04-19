# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2019 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import copy

import pytest
from twisted.trial import unittest

import yarss2.yarss_config
from yarss2.gtk3ui.dialog_rssfeed import DialogRSSFeed
from yarss2.util import http, logging
from yarss2.util.http import urlparse


class DummyClass(object):

    def __init__(self):
        self.rssfeed = None
        self.cookies = None

    def destroy(self):
        pass

    def save_rssfeed(self, rssfeed):
        pass


@pytest.mark.gui
class DialogRSSFeedTestCase(unittest.TestCase):

    def setUp(self):  # NOQA
        self.log = logging.getLogger(__name__)
        self.test_rssfeed = yarss2.yarss_config.get_fresh_rssfeed_config()

    def test_create(self):
        """Just test that the code runs"""
        dummy = DummyClass()
        DialogRSSFeed(dummy, self.test_rssfeed)

    def test_on_button_save_clicked(self):
        """Just test that the code runs"""
        dummy = DummyClass()
        rssfeed = yarss2.yarss_config.get_fresh_rssfeed_config()
        rssfeed["name"] = "Test"
        rssfeed["url"] = "http://test"
        rssfeed["update_interval"] = int(10)
        rssfeed["site"] = urlparse.urlparse("http://test.site.com/blabla/blalba.php").netloc
        rssfeed["obey_ttl"] = False

        rssfeed_copy = copy.copy(rssfeed)
        rssfeed_copy["name"] = "Test2"
        dummy.rssfeed = rssfeed_copy

        dialog = DialogRSSFeed(dummy, rssfeed)
        dialog.dialog = dummy
        dialog.glade.get_object("txt_name").set_text("Test2")
        dialog.on_button_save_clicked()

        # Should test the values that are saved

    def test_populate_data_fields(self):
        dummy = DummyClass()
        rssfeed = yarss2.yarss_config.get_fresh_rssfeed_config()
        domain = "testdomain.com"
        url = "http://%s/blabla/blalba.php" % domain
        rssfeed["name"] = "Test"
        rssfeed["url"] = url
        rssfeed["update_interval"] = int(10)
        rssfeed["site"] = urlparse.urlparse(url).netloc
        rssfeed["obey_ttl"] = False

        cookies = {'uid': '92323', 'passkey': 'aksdf9798d767sadf8678as6df9df'}
        dummy.rssfeed = rssfeed
        dummy.cookies = {'0': {'active': True, 'key': '0', 'site': domain, 'value': cookies}}
        dialog = DialogRSSFeed(dummy, rssfeed)
        dialog.dialog = dummy
        data = dialog.get_data_fields(cookies=True)
        self.assertEquals(data["name"], rssfeed["name"])
        self.assertEquals(data["url"], rssfeed["url"])
        self.assertEquals(data["obey_ttl"], rssfeed["obey_ttl"])
        self.assertEquals(data["update_interval"], rssfeed["update_interval"])
        self.assertEquals(data["site"], rssfeed["site"])
        cookies_hdr = http.get_cookie_header(cookies)
        self.assertEquals(data["cookies"], cookies_hdr.get("Cookie", ""))
