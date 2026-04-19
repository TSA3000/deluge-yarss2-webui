# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2019 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import twisted.internet.defer as defer
from twisted.trial import unittest

import deluge.component as component
from deluge.core import rpcserver
from deluge.core.rpcserver import DelugeRPCProtocol, RPCServer
from deluge.tests.basetest import BaseTestCase
from deluge.transfer import DelugeTransferProtocol

import yarss2.util.common
import yarss2.yarss_config
from yarss2.core import Core
from yarss2.torrent_handling import TorrentDownload, TorrentHandler
from yarss2.util import logging
from yarss2.yarss_config import get_user_agent

from . import common as test_common
from . import test_torrent_handling
from .base import TestCaseDebug
from .test_torrent_handling import TestComponent
from .utils.helpers import TempDir
from .utils.log_utils import plugin_tests_logger_name

log = logging.getLogger(plugin_tests_logger_name)

test_common.disable_new_release_check()


class CoreTestCase(unittest.TestCase):

    def setUp(self):  # NOQA
        defer.setDebugging(True)
        self.config = test_common.get_test_config()
        # get_test_config will load a new core.conf with the default values.
        # Must save to save to file so that torrent.py.TorrentOptions loads the default values
        self.config.core_config.save()
        test_component = TestComponent()
        self.torrent_handler = TorrentHandler(log)
        self.torrent_handler.download_torrent_file = test_component.download_torrent_file

        # Might be necessary for changes in master branch
        # yarss2.core.component = test_component

        self.core = Core("test")
        self.core.enable(config=self.config)
        self.core.torrent_handler = self.torrent_handler

    def tearDown(self):  # NOQA
        # Must stop loopingcalls or test fails
        self.core.disable()

#    def test_save_rssfeed(self):
#        config = test_common.get_test_config()
#        rssfeed = yarss2.yarss_config.get_fresh_rssfeed_config()
#
#        core = Core("YaRSS2")
#        core.enable(config=config)
#
#        core.save_rssfeed(self, dict_key=None, rssfeed_data=rssfeed, delete=False)
#
#        #default_subscription = yarss2.yarss_config.get_fresh_subscription_config()

    def test_add_torrent(self):
        torrent_name = "FreeBSD-9.0-RELEASE-amd64-dvd1.torrent"
        torrent_url = yarss2.util.common.get_resource(torrent_name, path="tests/data/")
        torrent_info = {"link": torrent_url}
        download_dict = self.core.add_torrent(torrent_info)
        download = TorrentDownload(download_dict)

        self.assertTrue(download.success, "Download failed, but should be True")
        self.assertEquals(torrent_url, test_torrent_handling.test_component.downloads.pop().torrent_url)
        self.assertEquals(test_torrent_handling.test_component.added.pop().filename, torrent_name)

    def test_add_torrent_default_user_agent(self):
        torrent_name = "FreeBSD-9.0-RELEASE-amd64-dvd1.torrent"
        torrent_url = yarss2.util.common.get_resource(torrent_name, path="tests/data/")
        torrent_info = {"link": torrent_url, "rssfeed_key": "0"}
        config = test_common.get_test_config_dict()
        default_user_agent = get_user_agent()
        self.config.set_config(config)
        self.core.yarss_config = self.config

        download_dict = self.core.add_torrent(torrent_info)
        self.assertEquals(download_dict["headers"]["User-Agent"], default_user_agent)

    def test_add_torrent_custom_user_agent(self):
        torrent_name = "FreeBSD-9.0-RELEASE-amd64-dvd1.torrent"
        torrent_url = yarss2.util.common.get_resource(torrent_name, path="tests/data/")
        torrent_info = {"link": torrent_url, "rssfeed_key": "0"}
        config = test_common.get_test_config_dict()
        custom_user_agent = "Custom user agent test"
        config["rssfeeds"]["0"]["user_agent"] = custom_user_agent
        self.config.set_config(config)
        self.core.yarss_config = self.config

        download_dict = self.core.add_torrent(torrent_info)
        self.assertEquals(download_dict["headers"]["User-Agent"], custom_user_agent)

    def test_initiate_rssfeed_update(self):
        config = test_common.get_test_config_dict()
        config["rssfeeds"]["0"]["update_interval"] = 30
        config["rssfeeds"]["0"]["obey_ttl"] = True
        config["rssfeeds"]["0"]["url"] = yarss2.util.common.get_resource(
            test_common.testdata_rssfeed_filename, path="tests")

        self.config.set_config(config)
        self.core.yarss_config = self.config

        self.add_torrents_called = False

        def add_torrents_pass(*arg):
            self.add_torrents_called = True

        self.core.rssfeed_scheduler.add_torrents_func = add_torrents_pass
        d = self.core.initiate_rssfeed_update(None, subscription_key="0")

        def callback_check(args):
            # Verify that add_torrents_pass was called
            self.assertTrue(self.add_torrents_called, "add_torrents has not been called")

        d.addCallback(callback_check)
        return d


class DelugeRPCProtocolTransferTester(DelugeTransferProtocol):

    def __init__(self, sessionno):
        super().__init__()
        self.messages_written = []
        self.messages_received = []
        self.sessionno = sessionno

    def write(self, data):
        self.messages_written.append(data)

    def message_received(self, message):
        self.messages_received.append(message)


class DelugeRPCProtocolTester(DelugeRPCProtocol):

    messages = []

    def __init__(self, sessionno):
        super().__init__()
        self.transport = DelugeRPCProtocolTransferTester(sessionno)

    def transfer_message(self, data):
        self.messages.append(data)
        super().transfer_message(data)


class RPCServerTestCase(BaseTestCase, TestCaseDebug):
    """
    This class tests that the exported RPC functions in core work throught the
    Deluge RPC protocol which requires all transmitted data to be serializable
    with rencode.
    """
    def set_up(self):
        self.set_unittest_maxdiff(None)
        self.rpcserver = RPCServer(listen=False)
        self.rpcserver.factory.protocol = DelugeRPCProtocolTester

        self.factory = self.rpcserver.factory
        self.session_id = '0'
        self.request_id = 11
        self.protocol = self.rpcserver.factory.protocol(self.session_id)
        self.protocol.factory = self.factory
        self.factory.session_protocols[self.session_id] = self.protocol
        self.factory.interested_events[self.session_id] = ['TorrentFolderRenamedEvent']
        self.protocol.sessionno = self.session_id
        self.factory.authorized_sessions[self.session_id] = self.protocol.AuthLevel(
            rpcserver.AUTH_LEVEL_DEFAULT, ''
        )

        self.config = test_common.get_test_config()
        self.core = Core("test")
        # Must call enable to create the RSSFeedScheduler in core
        self.core.enable(config=self.config)
        self.rpcserver.register_object(self.core)
        return component.start()

    def tear_down(self):
        def on_shutdown(result):
            del self.rpcserver

        return component.shutdown().addCallback(on_shutdown)

    def test_core_get_completion_paths(self):
        tmp_paths_dir = TempDir(prefix='yarss2_unit_tests')
        test_dirs = []

        for i in range(3):
            dirpath = tmp_paths_dir.mkdirs("dir%d" % (i))
            test_dirs.append("%s/" % dirpath)

        method = "core.get_completion_paths"
        args = []

        completion_text = "%s/d" % tmp_paths_dir.path
        arg = {
            "completion_text": completion_text,
            "show_hidden_files": False
        }
        args.append(arg)

        self.protocol.dispatch(self.request_id, method, args, {})
        msg_bytes = self.protocol.transport.messages_written[0]

        self.protocol.transport.dataReceived(msg_bytes)
        msg_received = self.protocol.transport.messages_received[0]

        self.assertEqual(msg_received[0], rpcserver.RPC_RESPONSE, str(msg_received))
        self.assertEqual(msg_received[1], self.request_id, str(msg_received))

        expected_result = dict(arg)
        expected_result.update({
            'paths': tuple(test_dirs),
        })
        self.assertEqual(expected_result, msg_received[2])

    def test_core_get_rssfeed_parsed(self):
        method = "core.get_rssfeed_parsed"
        args = []

        filename = "ezrss-rss-2.xml"
        file_url = yarss2.util.common.get_resource(filename, path="tests/data/feeds")

        rssfeed_data = {
            'active': True,
            'key': '3',
            'last_update': '2019-10-22T23:28:21+00:00',
            'name': 'hd-torrents.org',
            'obey_ttl': False,
            'prefer_magnet': False,
            'site': 'hd-torrents.org',
            'update_interval': 5,
            'update_on_startup': False,
            'url': file_url,
            'user_agent': ''
        }
        args.append(rssfeed_data)

        # Makes a call to core.get_rssfeed_parsed
        self.protocol.dispatch(self.request_id, method, args, {})

        msg_bytes = self.protocol.transport.messages_written[0]

        self.protocol.transport.dataReceived(msg_bytes)
        msg_received = self.protocol.transport.messages_received[0]

        self.assertEqual(msg_received[0], rpcserver.RPC_RESPONSE, str(msg_received))
        self.assertEqual(msg_received[1], self.request_id, str(msg_received))
        self.assertEqual(msg_received[2]['user_agent'], None)

        items = msg_received[2]['raw_result']['items']

        expected_item0 = {
            'title': 'Lolly Tang 2009 09 26 WEB x264-TBS',
            'link': 'https://eztv.io/ep/1369854/lolly-tang-2009-09-26-web-x264-tbs/',
            'description': None,
            'author': None,
            'categories': ('TV',),
            'comments': None,
            'enclosures': (
                {
                    'url': 'https://zoink.ch/torrent/Lolly.Tang.2009.09.26.WEB.x264-TBS[eztv].mkv.torrent',
                    'length': 288475596,
                    'type': 'application/x-bittorrent'
                },
            ),
            'guid': 'https://eztv.io/ep/1369854/lolly-tang-2009-09-26-web-x264-tbs/',
            'source': None,
            'torrent': {
                'filename': 'Lolly.Tang.2009.09.26.WEB.x264-TBS[eztv].mkv',
                'contentlength': '288475596',
                'infohash': '4CF874831F61F5DB9C3299E503E28A8103047BA0',
                'magneturi': 'magnet:?xt=urn:btih:4CF874831F61F5DB9C3299E503E28A8103047BA0&dn=Lolly.Tang.2009.09.26.WEB.x264-TBS%5Beztv%5D.mkv&tr=udp%3A%2F%2Ftracker.publicbt.com%2Fannounce&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=http%3A%2F%2Ftracker.trackerfix.com%3A80%2Fannounce&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969'  # noqa: E501
            },
            'torrent_item': None,
            'content_encoded': None,
            'published_date': '2019-09-27T08:12:48-04:00'
        }
        self.assertEqual(items[0], expected_item0)
