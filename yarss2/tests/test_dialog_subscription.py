# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2019 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import datetime
import re
from unittest import mock

import pytest
from twisted.internet import defer, threads
from twisted.trial import unittest

import deluge.common
import deluge.component as component
import deluge.config
import deluge.ui.client

import yarss2.gtk3ui.dialog_subscription
import yarss2.util.common
from yarss2 import yarss_config
from yarss2.gtk3ui.dialog_subscription import DialogSubscription
from yarss2.tests import common as tests_common
from yarss2.util import logging

from .utils.log_utils import plugin_tests_logger_name


class TestGTKUIBase(object):
    __test__ = False

    def __init__(self):
        self.labels = []

    def get_labels(self):
        return defer.succeed(self.labels)


class ComponentTestBase(unittest.TestCase):

    patch_component_start = True

    def setUp(self):  # NOQA
        if getattr(self, 'patch_component_start', False) is True:
            self.component_start_patcher = mock.patch('deluge.component.start')
            self.component_start_patcher.start()

    def tearDown(self):  # NOQA
        def on_shutdown(result):
            # Components aren't removed from registry in component.shutdown
            # so must do that manually
            component._ComponentRegistry.components = {}
            if getattr(self, 'patch_component_start', False) is True:
                self.component_start_patcher.stop()

        return component.shutdown().addCallback(on_shutdown)

    def enable_twisted_debug(self):
        defer.setDebugging(True)
        import twisted.internet.base
        twisted.internet.base.DelayedCall.debug = True


@pytest.mark.gui
class DialogSubscriptionTestCase(ComponentTestBase):

    def setUp(self):  # NOQA
        super().setUp()
        self.log = logging.getLogger(plugin_tests_logger_name)
        tests_common.set_tmp_config_dir()
        self.client = deluge.ui.client.client
        self.client.start_standalone()

    def test_rssfeed_selected(self):
        yarss2.gtk3ui.dialog_subscription.client = self.client

        def verify_result(empty, subscription_dialog):
            stored_items = tests_common.load_json_testdata()
            result = self.get_rssfeed_store_content(subscription_dialog)
            self.compare_dicts_content(stored_items, result)

        deferred = self.run_select_rssfeed(callback_func=verify_result)
        return deferred

    def test_select_rssfeed_with_search(self):
        subscription_config = yarss_config.get_fresh_subscription_config()
        search_regex = "bootonly"
        expected_match_count = 6
        subscription_config["regex_include"] = search_regex

        def verify_result(empty, subscription_dialog):
            result = self.get_rssfeed_store_content(subscription_dialog)
            p = re.compile(search_regex)
            match_count = 0
            for k in result:
                if result[k]["matches"] is True:
                    match_count += 1
                    self.assertTrue(p.search(result[k]["title"]))

            self.assertEquals(expected_match_count, match_count)

        deferred = self.run_select_rssfeed(subscription_config=subscription_config, callback_func=verify_result)
        return deferred

    def run_select_rssfeed(self, subscription_config=None, callback_func=None):
        config = self.get_test_config()

        if not subscription_config:
            subscription_config = yarss_config.get_fresh_subscription_config()

        subscription_dialog = DialogSubscription(TestGTKUIBase(),  # GTKUI
                                                 self.log,  # logger
                                                 subscription_config,
                                                 config["rssfeeds"],
                                                 {},  # self.email_messages,
                                                 {})  # self.cookies)

        def get_rssfeed_parsed(rssfeed_data, site_cookies_dict=None, user_agent=None):
            res = subscription_dialog.rssfeedhandler.get_rssfeed_parsed(rssfeed_data,
                                                                        site_cookies_dict=site_cookies_dict,
                                                                        user_agent=user_agent)
            return defer.succeed(res)

        with mock.patch.object(subscription_dialog, 'get_rssfeed_parsed', new=get_rssfeed_parsed):
            subscription_dialog.setup()

            def pass_func(*arg):
                return defer.succeed(None)

            class DialogWrapper(object):
                def __init__(self, dialog):
                    self.dialog = dialog

                def get_visible(self):
                    return True

            subscription_dialog.dialog = DialogWrapper(subscription_dialog.dialog)

            # Override the default selection callback
            subscription_dialog.method_perform_rssfeed_selection = pass_func

            # Sets the index 0 of rssfeed combox activated.
            rssfeeds_combobox = subscription_dialog.glade.get_object("combobox_rssfeeds")
            rssfeeds_combobox.set_active(0)

            deferred = subscription_dialog.perform_rssfeed_selection()
            deferred.addCallback(callback_func, subscription_dialog)
            return deferred

    def test_search(self):

        def run_search_test(empty, dialog_subscription):
            subscription_config = yarss_config.get_fresh_subscription_config()
            include_regex = ".*"
            exclude_regex = "64|MEMstick"
            expected_match_count = 7
            subscription_config["regex_include"] = include_regex
            subscription_config["regex_exclude"] = exclude_regex

            # Loading new config, and perform search
            dialog_subscription.load_basic_fields_data(subscription_config)
            dialog_subscription.perform_search()

            result = self.get_rssfeed_store_content(dialog_subscription)

            p_include = re.compile(include_regex,
                                   re.IGNORECASE if subscription_config["regex_include_ignorecase"] else 0)
            p_exclude = re.compile(exclude_regex,
                                   re.IGNORECASE if subscription_config["regex_exclude_ignorecase"] else 0)
            match_count = 0
            for k in result:
                if result[k]["matches"]:
                    match_count += 1
                    self.assertTrue(p_include.search(result[k]["title"]),
                                    "Expected '%s' to in '%s'" % (include_regex, result[k]["title"]))
                else:
                    self.assertTrue(p_exclude.search(result[k]["title"]),
                                    "Expected '%s' to in '%s'" % (exclude_regex, result[k]["title"]))
            self.assertEquals(match_count, expected_match_count)

        deferred = self.run_select_rssfeed(callback_func=run_search_test)
        return deferred

    def compare_dicts_content(self, dict1, dict2):
        """Compares the content of two dictionaries.
        If all the items of dict1 are found in dict2, returns True
        Returns True if there are items in dict2 that does not exist in dict1

        The keys do not have to be equal as long as the value of one key in dict1
        equals the value of some key in dict2.
        """
        for k1 in dict1.keys():
            for k2 in dict2.keys():
                if yarss2.util.common.dicts_equals(dict1[k1], dict2[k2]):
                    break
            else:
                raise AssertionError("Value for key '%s' in dict1 not found in dict2" % (k1))
        return True

    def get_rssfeed_store_content(self, subscription_dialog):
        store = subscription_dialog.matching_store
        it = store.get_iter_first()
        result = {}
        counter = 0

        while it:
            item = {}
            item["matches"] = store.get_value(it, 0)
            item["title"] = store.get_value(it, 1)
            item["updated"] = store.get_value(it, 2)
            item["updated_datetime"] = yarss2.util.common.isodate_to_datetime(store.get_value(it, 2))
            item["link"] = store.get_value(it, 3)
            item["torrent"] = store.get_value(it, 5)
            item["magnet"] = store.get_value(it, 6)
            result[str(counter)] = item
            counter += 1
            it = store.iter_next(it)
        return result

    def get_test_config(self):
        config = yarss2.yarss_config.default_prefs()
        file_url = yarss2.util.common.get_resource(tests_common.testdata_rssfeed_filename, path="tests")
        rssfeeds = tests_common.get_default_rssfeeds(2)
        subscriptions = tests_common.get_default_subscriptions(5)

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
        subscriptions["3"]["last_update"] = datetime.datetime.now().isoformat()
        subscriptions["4"]["name"] = "Wrong rsskey subscription"
        subscriptions["4"]["rssfeed_key"] = "1"

        config["rssfeeds"] = rssfeeds
        config["subscriptions"] = subscriptions
        return config

    def test_save_subscription(self):
        subscription_title = "Test subscription"
        regex_include = "Regex"
        config = self.get_test_config()
        testcase = self

        class TestGTKUI(TestGTKUIBase):
            def __init__(self):
                TestGTKUIBase.__init__(self)
                self.labels = ["Test_label"]

            def save_subscription(self, subscription_data):
                testcase.assertEquals(subscription_data["name"], subscription_title)
                testcase.assertEquals(subscription_data["regex_include"], regex_include)
                testcase.assertEquals(subscription_data["add_torrents_in_paused_state"], "True")
                testcase.assertEquals(subscription_data["auto_managed"], "False")
                testcase.assertEquals(subscription_data["sequential_download"], "Default")
                testcase.assertEquals(subscription_data["prioritize_first_last_pieces"], "Default")

        subscription_config = yarss_config.get_fresh_subscription_config()
        subscription_dialog = DialogSubscription(TestGTKUI(),  # GTKUI
                                                 self.log,  # logger
                                                 subscription_config,
                                                 config["rssfeeds"],
                                                 {},  # self.email_messages,
                                                 {})  # self.cookies)

        with mock.patch.object(subscription_dialog, 'get_rssfeed_parsed') as mocked_func:
            mocked_func.return_value = defer.succeed(None)
            subscription_dialog.setup()
            subscription_dialog.get_object("txt_name").set_text(subscription_title)
            subscription_dialog.get_object("txt_regex_include").set_text(regex_include)
            subscription_dialog.get_object("checkbox_add_torrents_in_paused_state_default").set_active(False)
            subscription_dialog.get_object("checkbox_add_torrents_in_paused_state").set_active(True)
            subscription_dialog.get_object("checkbutton_auto_managed_default").set_active(False)
            subscription_dialog.get_object("checkbutton_auto_managed").set_active(False)
            subscription_dialog.get_object("checkbutton_sequential_download_default").set_active(True)
            subscription_dialog.get_object("checkbutton_sequential_download").set_active(False)
            subscription_dialog.get_object("checkbutton_prioritize_first_last_default").set_active(True)
            subscription_dialog.get_object("checkbutton_prioritize_first_last").set_active(True)

            # Sets the index 0 of rssfeed combox activated.
            rssfeeds_combobox = subscription_dialog.get_object("combobox_rssfeeds")
            rssfeeds_combobox.set_active(0)
            return threads.deferToThread(subscription_dialog.save_subscription_data)

    def test_save_subscription_with_label(self):
        subscription_title = "Test subscription"
        config = self.get_test_config()
        testcase = self

        class TestGTKUI(unittest.TestCase, TestGTKUIBase):

            def __init__(self):
                TestGTKUIBase.__init__(self)
                self.labels = ["Test_label"]

            def save_subscription(self, subscription_data):
                testcase.assertEquals(subscription_data["label"], self.labels[0])

        subscription_config = yarss_config.get_fresh_subscription_config()
        subscription_dialog = DialogSubscription(TestGTKUI(),  # GTKUI
                                                 self.log,  # logger
                                                 subscription_config,
                                                 config["rssfeeds"],
                                                 {},  # self.email_messages,
                                                 {})  # self.cookies)
        with mock.patch.object(subscription_dialog, 'get_rssfeed_parsed') as mocked_func:
            mocked_func.return_value = defer.succeed(None)
            subscription_dialog.setup()
            subscription_dialog.glade.get_object("txt_name").set_text(subscription_title)

            # Sets the index 0 of rssfeed combox activated.
            rssfeeds_combobox = subscription_dialog.glade.get_object("combobox_rssfeeds")
            rssfeeds_combobox.set_active(0)
            return threads.deferToThread(subscription_dialog.save_subscription_data)

    @defer.inlineCallbacks
    def test_add_torrent_error(self):
        config = self.get_test_config()
        testcase = self

        class TestGTKUI(unittest.TestCase, TestGTKUIBase):

            def __init__(self):
                TestGTKUIBase.__init__(self)
                self.labels = ["Test_label"]

            def save_subscription(self, subscription_data):
                testcase.assertEquals(subscription_data["label"], self.labels[0])

            def add_torrent(self, torrent_link, subscription_data):
                torrent_download = {
                    'filedump': '<head>\n<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />\n<meta name="theme-color" content="#3860BB" />\n</head>\n<body>\n<script type="text/javascript" src="https://dyncdn.me/static/20/js/jquery-1.11.3.min.js"></script>\n<style type="text/css">a,abbr,acronym,address,applet,article,aside,audio,b,big,blockquote,body,canvas,caption,center,cite,code,dd,del,details,dfn,div,dl,dt,em,fieldset,figcaption,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,html,i,iframe,img,ins,kbd,label,legend,li,mark,menu,nav,object,ol,p,pre,q,s,samp,section,small,span,strike,strong,sub,summary,sup,table,tbody,td,tfoot,th,thead,time,tr,tt,u,ul,var,video{margin:0;padding:0;border:0;outline:0;font:inherit;vertical-align:baseline}article,aside,details,figcaption,figure,footer,header,hgroup,menu,nav,section{display:block}body{line-height:1}ol,ul{list-style:none}blockquote,q{quotes:none}blockquote:after,blockquote:before,q:after,q:before{content:\'\';content:none}ins{text-decoration:none}del{text-decoration:line-through}table{border-collapse:collapse;border-spacing:0}\nbody {\n    background: #000 url("https://dyncdn.me/static/20/img/bknd_body.jpg") repeat-x scroll 0 0 !important;\n    font: 400 8pt normal Tahoma,Verdana,Arial,Arial  !important;\n}\n.button {\n    background-color: #3860bb;\n    border: none;\n    color: white;\n    padding: 15px 32px;\n    text-align: center;\n    text-decoration: none;\n    display: inline-block;\n    font-size: 16px;\n    cursor: pointer;\n    text-transform: none;\n    overflow: visible;\n}\n.content-rounded {\n    background: #fff none repeat scroll 0 0 !important;\n    border-radius: 3px;\n    color: #000 !important;\n    padding: 20px;\n    width:961px;\n}\n</style><div align="center" style="margin-top:20px;padding-top:20px;color: #000 !important;">\n<div  class="content-rounded" style="color: #000 !important;">\n<img src="https://dyncdn.me/static/20/img/logo_dark_nodomain2_optimized.png"><br/>\nPlease wait while we try to verify your browser...<br/>\n<div style="font-weight: bold"><b>Please don\'t change tabs / minimize your browser or the process will fail</b></div><br/>\nIf you are stuck on this page disable your browser addons<br/><img src="https://dyncdn.me/static/20/img/loading_flat.gif">\n</div>\n</div>\n<script>\nvar w = window.innerWidth || document.documentElement.clientWidth || document.body.clientWidth;\nvar h = window.innerHeight || document.documentElement.clientHeight || document.body.clientHeight;\nvar days = 7;\nvar date = new Date();\nvar name = \'sk\';\nvar value_sk = \'pgjy3amc4u\';\nvar value_c = \'23842531\';\nvar value_i = \'1367198171\';\ndate.setTime(date.getTime()+(days*24*60*60*1000));\nvar expires = ";expires="+date.toGMTString();\ndocument.cookie = name+"="+value_sk+expires+"; path=/";\n\nif(w < 100 || h < 100) {\n\twindow.location.href = "/threat_defence.php?defence=nojc&r=38283315";\n} else {\n\tif(!document.domain) { var ref_cookie = \'\'; } else { var ref_cookie = document.domain; }\n\t$.ajax({type: \'GET\',url: \'/threat_defence_ajax.php?sk=\'+value_sk+\'&cid=\'+value_c+\'&i=\'+value_i+\'&r=25867870\',contentType: \'text/plain\', async: true, timeout: 3000, cache: false });\n\tsetTimeout(function(){\n\t\twindow.location.href = "/threat_defence.php?defence=2&sk="+value_sk+"&cid="+value_c+"&i="+value_i+"&ref_cookie="+ref_cookie+"&r=72304732";\n\t}, 5500);\n}\n</script>\n\t\t\n\n\t\t\n\t\t',  # noqa: E501
                    'error_msg': "Unable to decode torrent file! (unexpected end of file in bencoded string) URL: 'http://rarbg.to/rss_rt.php?id=k2jae9rlwn&m=t'",  # noqa: E501
                    'torrent_id': None,
                    'success': False,
                    'url': 'http://rarbg.to/rss_rt.php?id=k2jae9rlwn&m=t',
                    'is_magnet': False,
                    'cookies_dict': None,
                    'cookies': {},
                    'headers': {}}
                return defer.succeed(torrent_download)

        yield component.start()  # Necessary to avoid 'Reactor was unclean' error

        subscription_config = yarss_config.get_fresh_subscription_config()
        subscription_dialog = DialogSubscription(TestGTKUI(),  # GTKUI
                                                 self.log,  # logger
                                                 subscription_config,
                                                 config["rssfeeds"],
                                                 {},  # self.email_messages,
                                                 {})  # self.cookies)
        subscription_dialog.setup()

        torrent_link = "http://rarbg.to/rss_rt.php?id=k2jae9rlwn&m=t"
        success = yield subscription_dialog.add_torrent(torrent_link, None)
        self.assertFalse(success)
