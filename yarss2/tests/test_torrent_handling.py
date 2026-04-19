# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2019 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import datetime
import os.path
from unittest import mock

import requests
from twisted.trial import unittest

from deluge.error import AddTorrentError

import yarss2.torrent_handling
import yarss2.util.common
from yarss2.torrent_handling import TorrentDownload, TorrentHandler
from yarss2.util import logging
from yarss2.util.common import GeneralSubsConf, read_file

from . import common as test_common
from . import test_torrent_handling
from .utils.log_utils import plugin_tests_logger_name

test_component = None

log = logging.getLogger(plugin_tests_logger_name)


class TestComponent(object):
    __test__ = False

    def __init__(self, add_retval=True):
        global test_component
        test_component = self
        self.add_success = add_retval
        self.download_success = True
        self.downloads = []
        self.added = []
        self.use_filedump = None

    def add(self, filedump=None, filename=None, options=None, magnet=None):
        download = TorrentDownload()
        download.torrent_id = ""
        download.filedump = filedump
        download.filename = filename
        download.options = options
        download.magnet = magnet
        download.add_success = self.add_success
        self.added.append(download)
        return download

    def download_torrent_file(self, torrent_url, cookies=None, headers=None):
        download = TorrentDownload()
        download.torrent_url = torrent_url
        download.cookies = cookies
        download.headers = headers
        download.torrent_url = torrent_url
        download.success = self.download_success
        if self.use_filedump:
            download.filedump = self.use_filedump
        elif os.path.isfile(torrent_url):
            download.filedump = read_file(torrent_url)
        self.downloads.append(download)
        return download

    def get_enabled_plugins(self):
        return []

# When replacing component with test_component in modules,
# This is called e.g. when this is executed: component.get("TorrentManager")
# we ignore the key, and return the test component


def get(key):
    return test_component


# This makes sure that component.get("TorrentManager") returns
# the TestComponent, and not the deluge TorrentManager.
yarss2.torrent_handling.component = test_torrent_handling


def get_file(url, cookies={}, headers={}, verify=True):

    class Request(object):
        pass
    r = Request
    try:
        r.content = read_file(url)
    except Exception:
        pass
    return r


requests.get = get_file


class TorrentHandlingTestCase(unittest.TestCase):

    def setUp(self):  # NOQA
        self.log = log
        self.config = test_common.get_test_config()
        # get_test_config will load a new core.conf with the default values.
        # Must save to save to file so that torrent.py.TorrentOptions loads the default values
        self.config.core_config.save()
        global test_component
        test_component = TestComponent(add_retval=True)

    def test_add_torrent(self):
        handler = TorrentHandler(self.log)
        filename = yarss2.util.common.get_resource("FreeBSD-9.0-RELEASE-amd64-dvd1.torrent", path="tests/data/")
        torrent_info = {"link": filename, "site_cookies_dict": {}}
        torrent_download = handler.add_torrent(torrent_info)

        torrent_added = test_component.added.pop()
        self.assertTrue(torrent_added.success)
        self.assertFalse(torrent_added.filedump is None, "Filedump is not None")
        self.assertEquals(torrent_added.filename, os.path.split(filename)[1])
        self.assertFalse(torrent_added.filedump is None)
        self.assertEquals(torrent_download.url, filename)

    def test_add_torrent_raise_AddTorrentError(self):  # noqa: N802
        handler = TorrentHandler(self.log)
        filename = yarss2.util.common.get_resource("FreeBSD-9.0-RELEASE-amd64-dvd1.torrent", path="tests/data/")
        torrent_info = {"link": filename, "site_cookies_dict": {}}

        with mock.patch.object(TestComponent, 'add') as test_component_add:
            test_component_add.side_effect = AddTorrentError('Torrent already in session (%s).' % 1)
            torrent_added = handler.add_torrent(torrent_info)
            self.assertFalse(torrent_added.success)

    def test_add_torrent_magnet_link(self):
        handler = TorrentHandler(self.log)
        torrent_url = "magnet:blbalba/url.magnet.link"
        torrent_info = {"link": torrent_url, "site_cookies_dict": {}}
        download = handler.add_torrent(torrent_info)
        self.assertTrue(download.success)
        self.assertTrue(download.is_magnet)
        self.assertEquals(test_component.added.pop().magnet, torrent_url)

    def test_add_torrent_ret_false(self):
        handler = TorrentHandler(self.log)
        torrent_url = "http://url.com/file.torrent"
        cookies = {}
        global test_component
        test_component.download_success = False
        handler.download_torrent_file = test_component.download_torrent_file
        torrent_info = {"link": torrent_url, "site_cookies_dict": cookies}
        torrent_download = handler.add_torrent(torrent_info)
        self.assertFalse(torrent_download.success)
        # Set by download_torrent_file
        self.assertEquals(torrent_download.torrent_url, torrent_url)
        self.assertEquals(torrent_download.cookies, cookies)
        test_component.download_success = True

    def test_add_torrent_with_subscription_data(self):
        handler = TorrentHandler(self.log)
        subscription_data = yarss2.yarss_config.get_fresh_subscription_config()
        subscription_data["move_completed"] = "move/path"
        subscription_data["download_location"] = "download/path"
        subscription_data["add_torrents_in_paused_state"] = GeneralSubsConf.DEFAULT

        download = TorrentDownload()
        torrent_info = {"link": "http://url.com/file.torrent",
                        "site_cookies_dict": {},
                        "subscription_data": subscription_data,
                        "torrent_download": download}

        d = handler.add_torrent(torrent_info)
        self.assertTrue(d.success)
        added = test_component.added.pop()
        self.assertTrue(added.options["move_completed"])
        self.assertEquals(added.options["move_completed_path"], subscription_data["move_completed"])
        self.assertEquals(added.options["download_location"], subscription_data["download_location"])
        # When using DEFAULT, the default value for add_paused on TorrentSettings is False
        self.assertEquals(added.options["add_paused"], False)

    def test_get_torrent(self):
        handler = TorrentHandler(self.log)
        handler.download_torrent_file = test_component.download_torrent_file
        filename = yarss2.util.common.get_resource("FreeBSD-9.0-RELEASE-amd64-dvd1.torrent", path="tests/data/")
        test_component.use_filedump = read_file(filename)
        torrent_info = {"link": "http://url.com/file.torrent",
                        "site_cookies_dict": {"cookiekey": "cookievalue"},
                        "user_agent": "test"}
        download = handler.get_torrent(torrent_info)
        self.assertEquals(download.headers, {'User-Agent': 'test'})
        self.assertEquals(download.cookies, {'cookiekey': 'cookievalue'})
        self.assertFalse(download.is_magnet)

    def test_get_torrent_magnet(self):
        handler = TorrentHandler(self.log)
        torrent_info = {"link": "magnet:hash"}
        download = handler.get_torrent(torrent_info)
        self.assertTrue(download.is_magnet)

    def get_test_rssfeeds_match_dict(self):
        match_option_dict = {}
        match_option_dict["regex_include"] = ""
        match_option_dict["regex_exclude"] = ""
        match_option_dict["regex_include_ignorecase"] = True
        match_option_dict["regex_exclude_ignorecase"] = True
        match_option_dict["custom_text_lines"] = None

        rssfeed_matching = {}
        rssfeed_matching["0"] = {"matches": False, "link": "", "title": "FreeBSD-9.0-RELEASE-amd64-all"}
        rssfeed_matching["1"] = {"matches": False, "link": "", "title": "FreeBSD-9.0-RELEASE-i386-all"}
        rssfeed_matching["2"] = {"matches": False, "link": "", "title": "fREEbsd-9.0-RELEASE-i386-all"}
        return match_option_dict, rssfeed_matching

    def test_add_torrents(self):
        handler = TorrentHandler(self.log)
        from yarss2.rssfeed_handling import RSSFeedHandler
        self.rssfeedhandler = RSSFeedHandler(self.log)

        # Override method download_torrent_file
        handler.download_torrent_file = test_component.download_torrent_file
        filename = yarss2.util.common.get_resource("FreeBSD-9.0-RELEASE-amd64-dvd1.torrent", path="tests/data/")
        test_component.use_filedump = read_file(filename)

        config = get_test_config_dict()                                # 0 is the rssfeed key
        match_result = self.rssfeedhandler.fetch_feed_torrents(config, "0")
        matching_torrents = match_result["matching_torrents"]
        saved_subscriptions = []

        def save_subscription_func(subscription_data):
            saved_subscriptions.append(subscription_data)

        handler.add_torrents(save_subscription_func, matching_torrents, self.config.get_config())
        self.assertEquals(len(saved_subscriptions), 3)
        handler.use_filedump = None

####################################
# Helper methods for test data
####################################


def get_test_config_dict():
    config = yarss2.yarss_config.default_prefs()
    file_url = yarss2.util.common.get_resource(test_common.testdata_rssfeed_filename, path="tests")
    rssfeeds = test_common.get_default_rssfeeds(3)
    subscriptions = test_common.get_default_subscriptions(5)

    rssfeeds["0"]["name"] = "Test RSS Feed"
    rssfeeds["0"]["url"] = file_url
    rssfeeds["1"]["name"] = "Test RSS Feed2"
    rssfeeds["1"]["active"] = False

    subscriptions["0"]["name"] = "Matching subscription"
    subscriptions["0"]["regex_include"] = "sparc64"
    subscriptions["1"]["name"] = "Non-matching subscription"
    subscriptions["1"]["regex_include"] = None
    subscriptions["2"]["name"] = "Inactive subscription"
    subscriptions["2"]["active"] = False
    subscriptions["3"]["name"] = "Update_time too new"
    subscriptions["3"]["last_match"] = datetime.datetime.now().isoformat()
    subscriptions["4"]["name"] = "Wrong rsskey subscription"
    subscriptions["4"]["rssfeed_key"] = "1"

    config["rssfeeds"] = rssfeeds
    config["subscriptions"] = subscriptions
    return config
