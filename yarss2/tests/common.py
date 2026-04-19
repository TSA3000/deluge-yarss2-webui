# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2015 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import datetime
import json
import tempfile

import deluge.config
import deluge.configmanager
import deluge.core.preferencesmanager

import yarss2.util.common
from yarss2 import load_libs, yarss_config
from yarss2.util import logging

from .utils.log_utils import plugin_tests_logger_name

load_libs()

log = logging.getLogger(plugin_tests_logger_name)


def disable_new_release_check():
    import deluge.core.preferencesmanager
    deluge.core.preferencesmanager.DEFAULT_PREFS["new_release_check"] = False


disable_new_release_check()


def get_default_subscriptions(count):
    subscriptions = {}
    for i in range(count):
        subscriptions[str(i)] = yarss_config.get_fresh_subscription_config(
            name="Non-matching subscription",
            last_match=yarss2.util.common.get_default_date().isoformat(),
            rssfeed_key="0", key=str(i), regex_include=None, regex_exclude=None)
    return subscriptions


def get_default_rssfeeds(count):
    d = {}
    for i in range(count):
        d[str(i)] = yarss_config.get_fresh_rssfeed_config(key=str(i))
    return d


def get_test_config(config_filename="yarss_test.conf", config_dir=None, verify_config=True):
    """Creates a YaRSS2 config with a reference to a proper deluge config"""
    if config_dir is None:
        config_dir = set_tmp_config_dir()
    deluge_config = deluge.config.Config(config_filename,
                                         yarss2.yarss_config.default_prefs(), config_dir=config_dir)
    core_config = deluge.config.Config("core.conf", defaults=deluge.core.preferencesmanager.DEFAULT_PREFS,
                                       config_dir=config_dir)
    config = yarss2.yarss_config.YARSSConfig(log, config=deluge_config, core_config=core_config,
                                             verify_config=verify_config)
    return config


def set_tmp_config_dir():
    config_directory = tempfile.mkdtemp()
    deluge.configmanager.set_config_dir(config_directory)
    return config_directory


# http://torrents.freebsd.org:8080/rss.xml
testdata_rssfeed_filename = "data/feeds/freebsd_rss.xml"
testdata_rss_itmes_json_filename = "data/freebsd_rss_items_dump.json"


def load_json_testdata():
    return json_load(testdata_rss_itmes_json_filename, dict_int_keys=True)


def json_load(filename, dict_int_keys=False):
    def datetime_parse(dct):
        if 'updated' in dct:
            # Add timezone (+0000)
            updated_dt = yarss2.util.common.isodate_to_datetime(dct["updated"])
            dct["updated"] = updated_dt.isoformat()
        return dct

    filename = yarss2.util.common.get_resource(filename, path="tests")
    f = open(filename, "r")
    d = json.load(f, object_hook=datetime_parse)
    f.close()

    # Must change keys from string to int
    if dict_int_keys:
        for key in list(d.keys()):
            d[int(key)] = d[key]
            del d[key]
    return d


def json_dump(obj, filename):
    filename = yarss2.util.common.get_resource(filename, path="tests")
    f = open(filename, "wb")
    json.dump(obj, f, indent=2, cls=DatetimeEncoder)
    f.flush()
    f.close()


class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


####################################
# Helper methods for test data
####################################

def get_test_config_dict():
    config = yarss2.yarss_config.default_prefs()
    file_url = yarss2.util.common.get_resource(testdata_rssfeed_filename, path="tests")
    rssfeeds = get_default_rssfeeds(3)
    subscriptions = get_default_subscriptions(5)

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
