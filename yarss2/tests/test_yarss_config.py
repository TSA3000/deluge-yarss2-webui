# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2019 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#
import shutil

from twisted.trial import unittest

import yarss2.util.common
import yarss2.yarss_config
from yarss2.util.common import GeneralSubsConf

from . import common as test_common

try:
    unicode  # noqa: F821 undefined name
except NameError:
    unicode = str


class ConfigTestCase(unittest.TestCase):

    def setUp(self):  # NOQA
        self.config = test_common.get_test_config(verify_config=False)

    def test_insert_missing_dict_values(self):
        default_subscription = yarss2.yarss_config.get_fresh_subscription_config()
        subscription_del = yarss2.yarss_config.get_fresh_subscription_config()

        # Remove some keys from default subscription
        del subscription_del["regex_include"]
        del subscription_del["email_notifications"]

        self.config._insert_missing_dict_values(subscription_del, default_subscription, level=1)
        key_diff = set(default_subscription.keys()) - set(subscription_del.keys())
        self.assertTrue(not key_diff)

        subscription_del = yarss2.yarss_config.get_fresh_subscription_config()
        # Remove some keys from default subscription
        del subscription_del["regex_include"]
        del subscription_del["email_notifications"]

        conf = {"0": subscription_del}
        self.config._insert_missing_dict_values(conf, default_subscription, level=2)
        key_diff = set(default_subscription.keys()) - set(subscription_del.keys())
        self.assertTrue(not key_diff)

    def test_verify_types_config_elements(self):
        # Need a valid rssfeed in the config
        rssfeed_key = "0"
        self.config.config["rssfeeds"][rssfeed_key] = yarss2.yarss_config.get_fresh_rssfeed_config(key=rssfeed_key)
        default_subscription = yarss2.yarss_config.get_fresh_subscription_config()
        subscriptions = test_common.get_default_subscriptions(2)

        for i in range(2):
            subscriptions[str(i)]["name"] = None
            subscriptions[str(i)]["active"] = ""
            subscriptions[str(i)]["key"] = ""
            subscriptions[str(i)]["rssfeed_key"] = rssfeed_key

        changed = self.config._verify_types_config_elements(subscriptions, default_subscription)
        self.assertTrue(changed)

        for i in range(2):
            self.assertEquals(subscriptions[str(i)]["name"], default_subscription["name"])
            self.assertEquals(subscriptions[str(i)]["active"], default_subscription["active"])

    def test_verify_types_values_changed(self):
        # 0 is just a key value (could be any number)
        rssfeed_key = "0"
        subscription_key = "0"
        # Default must have a different key than the test subscription, so set to ""
        # Need a valid rssfeed in the config
        self.config.config["rssfeeds"][rssfeed_key] = yarss2.yarss_config.get_fresh_rssfeed_config(key=rssfeed_key)
        default_subscription = yarss2.yarss_config.get_fresh_subscription_config(key="")
        subscription_changed = yarss2.yarss_config.get_fresh_subscription_config(key=subscription_key)

        # Change type of the value for some keys
        subscription_changed["regex_include"] = None                # Should be unicode
        subscription_changed["email_notifications"] = []            # Should be dict
        subscription_changed["regex_include_ignorecase"] = ""       # Should be boolean
        subscription_changed["rssfeed_key"] = unicode(rssfeed_key)  # Should be str
        subscription_changed["key"] = None                          # Should be str

        changed = self.config._verify_types(subscription_key, subscription_changed, default_subscription)
        self.assertTrue(changed)
        self.assertEquals(subscription_changed["regex_include"], default_subscription["regex_include"])
        self.assertEquals(subscription_changed["email_notifications"], default_subscription["email_notifications"])
        self.assertEquals(subscription_changed["regex_include_ignorecase"],
                          default_subscription["regex_include_ignorecase"])
        self.assertEquals(subscription_changed["key"], subscription_key)

    def test_verify_types_values_deleted(self):
        rssfeed_key = "0"
        subscription_key = "0"
        # Need a valid rssfeed in the config
        self.config.config["rssfeeds"][rssfeed_key] = yarss2.yarss_config.get_fresh_rssfeed_config(key=rssfeed_key)
        default_subscription = yarss2.yarss_config.get_fresh_subscription_config(key=subscription_key)
        subscription_changed = yarss2.yarss_config.get_fresh_subscription_config(key=subscription_key)

        # Remove some keys from default subscription
        subscription_changed["name"] = "Not default"
        subscription_changed["rssfeed_key"] = rssfeed_key
        del subscription_changed["regex_include"]
        del subscription_changed["email_notifications"]
        del subscription_changed["key"]

        changed = self.config._verify_types(subscription_key, subscription_changed, default_subscription)
        self.assertTrue(changed)
        self.assertEquals(subscription_changed["regex_include"], default_subscription["regex_include"])
        self.assertEquals(subscription_changed["email_notifications"], default_subscription["email_notifications"])

        # Here, the missing key value should be set to subscription_key, and not the default value (which doesn't exist)
        self.assertEquals(subscription_changed["key"], subscription_key)

        # Verify that the value of regex_exclude has been converted to unicode
        self.assertEquals(type(subscription_changed["regex_exclude"]), unicode)

    def test_verify_types_rssfeed_key_invalid_default_values(self):
        """Test if rssfeed_key is invalid in a subscription, and the subscription has the default values
        In that case, the subscription should be deleted"""
        config_key = "0"
        default_subscription = yarss2.yarss_config.get_fresh_subscription_config(key=config_key)

        # rssfeed_key is not an integer
        subscription_changed = yarss2.yarss_config.get_fresh_subscription_config(key=config_key)
        subscription_changed["rssfeed_key"] = ""
        changed = self.config._verify_types(config_key, subscription_changed, default_subscription)
        self.assertTrue(changed)
        # Since the subscription has the default values, all values should now be deleted
        self.assertEquals(len(subscription_changed.keys()), 0)

        # rssfeed_key has invalid type
        subscription_changed = yarss2.yarss_config.get_fresh_subscription_config(key=config_key)
        subscription_changed["rssfeed_key"] = True
        changed = self.config._verify_types(config_key, subscription_changed, default_subscription)
        self.assertTrue(changed)
        # Since the subscription has the default values, all values should now be deleted
        self.assertEquals(len(subscription_changed.keys()), 0)

        # rssfeed_key doesn't exist
        subscription_changed = yarss2.yarss_config.get_fresh_subscription_config(key=config_key)
        del subscription_changed["rssfeed_key"]
        changed = self.config._verify_types(config_key, subscription_changed, default_subscription)
        self.assertTrue(changed)
        # Since the subscription has the default values, all values should now be deleted
        self.assertEquals(len(subscription_changed.keys()), 0)

    def test_verify_types_rssfeed_key_invalid_non_default_values(self):
        """Test if rssfeed_key is invalid in a subscription, and the subscription has NON-default values
        In that case, a dummy rssfeed should be create (if it doesn't exist), and the subscription should be given
        the rssfeed_key of the dummy"""
        config_key = "0"
        default_subscription = yarss2.yarss_config.get_fresh_subscription_config(key=config_key)

        # rssfeed_key is not an integer
        subscription_changed = yarss2.yarss_config.get_fresh_subscription_config(key=config_key)
        subscription_changed["rssfeed_key"] = ""
        subscription_changed["name"] = u"Not default"
        changed = self.config._verify_types(config_key, subscription_changed, default_subscription)
        self.assertTrue(changed, "_verify_types did not change the config")
        # rssfeed_key should be the DUMMY_RSSFEED_KEY
        self.assertTrue(yarss2.yarss_config.DUMMY_RSSFEED_KEY in self.config.config["rssfeeds"])

        # rssfeed_key has invalid type
        subscription_changed = yarss2.yarss_config.get_fresh_subscription_config(key=config_key)
        subscription_changed["rssfeed_key"] = True
        subscription_changed["name"] = u"Not default"
        changed = self.config._verify_types(config_key, subscription_changed, default_subscription)
        self.assertTrue(changed)
        # rssfeed_key should be the DUMMY_RSSFEED_KEY
        self.assertTrue(yarss2.yarss_config.DUMMY_RSSFEED_KEY in self.config.config["rssfeeds"])

        # rssfeed_key doesn't exist
        subscription_changed = yarss2.yarss_config.get_fresh_subscription_config(key=config_key)
        del subscription_changed["rssfeed_key"]
        subscription_changed["name"] = u"Not default"
        changed = self.config._verify_types(config_key, subscription_changed, default_subscription)
        self.assertTrue(changed)
        # rssfeed_key should be the DUMMY_RSSFEED_KEY
        self.assertTrue(yarss2.yarss_config.DUMMY_RSSFEED_KEY in self.config.config["rssfeeds"])

    def test_verify_config(self):
        default_subscription = yarss2.yarss_config.get_fresh_subscription_config()
        test_feeds = test_common.get_default_rssfeeds(2)
        test_subscriptions = test_common.get_default_subscriptions(3)
        test_subscriptions["0"]["rssfeed_key"] = "0"
        test_subscriptions["1"]["rssfeed_key"] = "0"
        test_subscriptions["0"]["name"] = True  # Wrong type

        del test_subscriptions["0"]["regex_include"]
        del test_subscriptions["1"]["key"]
        del test_subscriptions["2"]["rssfeed_key"]

        email_conf = yarss2.yarss_config.get_fresh_email_config()
        del email_conf["default_email_to_address"]

        self.config.config["rssfeeds"] = test_feeds
        self.config.config["subscriptions"] = test_subscriptions
        self.config.config["email_configurations"] = email_conf
        self.config._verify_config()

        # Should have the key reinserted
        self.assertEquals(test_subscriptions["1"]["key"], "1")
        # Name should be default value
        self.assertEquals(test_subscriptions["0"]["name"], default_subscription["name"])
        # regex_include should be reinserted with the default value
        self.assertTrue("regex_include" in test_subscriptions["0"])
        # The rssfeed_key should be the dummy
        self.assertEquals(test_subscriptions["2"]["rssfeed_key"], yarss2.yarss_config.DUMMY_RSSFEED_KEY)
        # The dummy should now exist in rssfeeds dict
        self.assertTrue(yarss2.yarss_config.DUMMY_RSSFEED_KEY in test_feeds)
        self.assertTrue("default_email_to_address" in self.config.config["email_configurations"])

    def test_update_config_to_version4(self):
        # default_subscription = yarss2.yarss_config.get_fresh_subscription_config()
        # Create 2 feeds
        test_feeds = test_common.get_default_rssfeeds(2)
        # Create 3 subscriptions
        test_subscriptions = test_common.get_default_subscriptions(2)

        last_match_value = test_subscriptions["0"]["last_match"]
        # Old config had last_update instead of last_match
        test_subscriptions["0"]["last_update"] = test_subscriptions["0"]["last_match"]
        del test_subscriptions["0"]["last_match"]

        # Replace field last_update with last_match
        self.config.config["rssfeeds"] = test_feeds
        self.config.config["subscriptions"] = test_subscriptions

        # Call the function that makes the changes
        self.config._verify_config()

        # Test that last_update was replaced with last_match
        self.assertTrue("last_match" in test_subscriptions["0"])
        self.assertFalse("last_update" in test_subscriptions["0"])
        self.assertEquals(test_subscriptions["0"]["last_match"], last_match_value)

    def test_update_config_to_version5(self):
        # default_subscription = yarss2.yarss_config.get_fresh_subscription_config()
        # Create 2 feeds
        test_feeds = test_common.get_default_rssfeeds(2)
        # Create 3 subscriptions
        test_subscriptions = test_common.get_default_subscriptions(2)

        # Replace field last_update with last_match
        self.config.config["rssfeeds"] = test_feeds
        self.config.config["subscriptions"] = test_subscriptions
        self.config.config["cookies"] = {"0": {
            "active": True,
            "value": [["uid", "175728"], ["pass", "3421d1a00b48397a874454626decec04"]],
            "site": "bitmetv.org",
            "key": "0"}}

        test_subscriptions["0"]["add_torrents_in_paused_state"] = True
        test_subscriptions["1"]["add_torrents_in_paused_state"] = False

        # Call the function that makes the changes
        self.config._verify_config()

        # Test changes for "add_torrents_in_paused_state_to_GeneralSubsConf"
        self.assertEquals(test_subscriptions["0"]["add_torrents_in_paused_state"], GeneralSubsConf.ENABLED)
        self.assertEquals(test_subscriptions["1"]["add_torrents_in_paused_state"], GeneralSubsConf.DISABLED)

        # Test changes for "change_value_from_list_to_dict"
        values = self.config.config["cookies"]["0"]["value"]
        self.assertTrue(type(values) is dict)
        self.assertTrue("uid" in values)
        self.assertEquals(values["uid"], "175728")
        self.assertTrue("pass" in values)
        self.assertEquals(values["pass"], "3421d1a00b48397a874454626decec04")

    def test_update_config_file_to_version2(self):
        config_file = "yarss2_v1.conf"
        filename = yarss2.util.common.get_resource(config_file, path="tests/data/")
        tmp_dir = test_common.set_tmp_config_dir()
        shutil.copy(filename, tmp_dir)
        self.config = test_common.get_test_config(config_filename=config_file, config_dir=tmp_dir, verify_config=False)

        # Call the function that makes the changes
        self.config.config.run_converter((0, 1), 2, self.config.update_config_to_version2)

        # 1 - search field from subscription was removed
        # 2 - Added field 'custom_text_lines'
        subscriptions = self.config.config["subscriptions"]
        for key in subscriptions:
            self.assertFalse("search" in subscriptions[key], "Field 'search still exists'")
            self.assertTrue("custom_text_lines" in subscriptions[key], "Field 'custom_text_lines' does not exist!")

        self.assertEquals(self.config.config._Config__version["file"], 2)

    def test_update_config_file_to_version3(self):
        config_file = "yarss2_v2.conf"
        filename = yarss2.util.common.get_resource(config_file, path="tests/data/")
        tmp_dir = test_common.set_tmp_config_dir()
        shutil.copy(filename, tmp_dir)
        self.config = test_common.get_test_config(config_filename=config_file, config_dir=tmp_dir, verify_config=False)

        # Call the function that makes the changes
        self.config.config.run_converter((2, 2), 3, self.config.update_config_to_version3)

        # Added field 'download_location'
        for key in self.config.config["subscriptions"]:
            self.assertTrue("download_location" in self.config.config["subscriptions"][key],
                            "Field 'download_location' does not exist!")

        for key in self.config.config["rssfeeds"]:
            self.assertTrue("obey_ttl" in self.config.config["rssfeeds"][key], "Field 'obey_ttl' does not exist!")

        self.assertEquals(self.config.config._Config__version["file"], 3)

    def test_update_config_file_to_version4(self):
        config_file = "yarss2_v3.conf"
        filename = yarss2.util.common.get_resource(config_file, path="tests/data/")
        tmp_dir = test_common.set_tmp_config_dir()
        shutil.copy(filename, tmp_dir)
        self.config = test_common.get_test_config(config_filename=config_file, config_dir=tmp_dir, verify_config=False)

        subscription_keys = self.config.config["subscriptions"].keys()
        last_update_values = [self.config.config["subscriptions"][key]["last_update"] for key in subscription_keys]

        # Call the function that makes the changes
        self.config.config.run_converter((3, 3), 4, self.config.update_config_to_version4)

        for i, key in enumerate(subscription_keys):
            # Test changes for "replace_last_update_with_last_match"
            self.assertTrue("last_match" in self.config.config["subscriptions"][key])
            self.assertFalse("last_update" in self.config.config["subscriptions"][key])
            self.assertEquals(self.config.config["subscriptions"][key]["last_match"], last_update_values[i])

        self.assertEquals(self.config.config._Config__version["file"], 4)

    def test_update_config_file_to_version5(self):
        config_file = "yarss2_v4.conf"
        filename = yarss2.util.common.get_resource(config_file, path="tests/data/")
        tmp_dir = test_common.set_tmp_config_dir()
        shutil.copy(filename, tmp_dir)
        self.config = test_common.get_test_config(config_filename=config_file, config_dir=tmp_dir, verify_config=False)

        # Call the function that makes the changes
        self.config.config.run_converter((4, 4), 5, self.config.update_config_to_version5)

        # Test changes for "add_torrents_in_paused_state_to_GeneralSubsConf"
        self.assertEquals(self.config.config["subscriptions"]["0"]["add_torrents_in_paused_state"],
                          GeneralSubsConf.DISABLED)
        self.assertEquals(self.config.config["subscriptions"]["1"]["add_torrents_in_paused_state"],
                          GeneralSubsConf.ENABLED)

        for key in self.config.config["subscriptions"].keys():
            # last_update replaced with last_match
            self.assertFalse("last_update" in self.config.config["subscriptions"][key])
            self.assertTrue("last_match" in self.config.config["subscriptions"][key])

            # Add in paused state should be unicode
            self.assertEquals(type(self.config.config["subscriptions"][key]["add_torrents_in_paused_state"]), unicode)

            self.assertTrue("max_upload_slots" in self.config.config["subscriptions"][key])
            self.assertTrue("max_connections" in self.config.config["subscriptions"][key])
            self.assertTrue("max_upload_speed" in self.config.config["subscriptions"][key])
            self.assertTrue("prioritize_first_last_pieces" in self.config.config["subscriptions"][key])
            self.assertTrue("auto_managed" in self.config.config["subscriptions"][key])
            self.assertTrue("sequential_download" in self.config.config["subscriptions"][key])

        # Test changes for "change_value_from_list_to_dict"
        for cookie in self.config.config["cookies"].values():
            self.assertEquals(type(cookie["value"]), dict)

        self.assertEquals(self.config.config._Config__version["file"], 5)

    def test_update_config_file_to_version6(self):
        config_file = "yarss2_v5.conf"
        filename = yarss2.util.common.get_resource(config_file, path="tests/data/")
        tmp_dir = test_common.set_tmp_config_dir()
        shutil.copy(filename, tmp_dir)
        self.config = test_common.get_test_config(config_filename=config_file, config_dir=tmp_dir, verify_config=False)

        # Call the function that makes the changes
        self.config.config.run_converter((5, 5), 6, self.config.update_config_to_version6)

        for key in self.config.config["subscriptions"].keys():
            self.assertTrue("ignore_timestamp" in self.config.config["subscriptions"][key])
            self.assertFalse(self.config.config["subscriptions"][key]["ignore_timestamp"])

            self.assertTrue("label" in self.config.config["subscriptions"][key])
            self.assertEquals(self.config.config["subscriptions"][key]["label"], "")

        # Test changes for "change_value_from_list_to_dict"
        for rssfeed in self.config.config["rssfeeds"].values():
            self.assertTrue("user_agent" in rssfeed)
            self.assertEquals(rssfeed["user_agent"], "")

        self.assertEquals(self.config.config._Config__version["file"], 6)

    def test_update_config_file_from_1_0(self):
        tmp_dir = test_common.set_tmp_config_dir()
        # Copy the yarss2_v1.conf file to test dir to avoid changes to the file.
        config_file = "yarss2_v1.conf"
        filename = yarss2.util.common.get_resource(config_file, path="tests/data/")
        shutil.copy(filename, tmp_dir)
        self.config = test_common.get_test_config(config_filename=config_file, config_dir=tmp_dir, verify_config=False)

        self.assertEquals(self.config.config._Config__version["format"], 1)
        self.assertEquals(self.config.config._Config__version["file"], 1)

        # Verify that the old values are what we expect
        for key in self.config.config["cookies"].keys():
            self.assertEquals(type(self.config.config["cookies"][key]["value"]), list)

        # Update the config
        self.config._verify_config()

        for key in self.config.config["cookies"].keys():
            self.assertEquals(type(self.config.config["cookies"][key]["value"]), dict)

        for key in self.config.config["subscriptions"].keys():
            # last_update replaced with last_match
            self.assertFalse("last_update" in self.config.config["subscriptions"][key])
            self.assertTrue("last_match" in self.config.config["subscriptions"][key])

            # Add in paused state should be string
            self.assertEquals(type(self.config.config["subscriptions"][key]["add_torrents_in_paused_state"]), unicode)

            self.assertTrue("max_upload_slots" in self.config.config["subscriptions"][key])
            self.assertTrue("max_connections" in self.config.config["subscriptions"][key])
            self.assertTrue("max_upload_speed" in self.config.config["subscriptions"][key])
            self.assertTrue("prioritize_first_last_pieces" in self.config.config["subscriptions"][key])
            self.assertTrue("auto_managed" in self.config.config["subscriptions"][key])
            self.assertTrue("sequential_download" in self.config.config["subscriptions"][key])

        # Test cookie type
        for cookie in self.config.config["cookies"].values():
            self.assertEquals(type(cookie["value"]), dict)

        self.assertEquals(self.config.config._Config__version["format"], 1)

    def test_update_config_file_from_1_2_beta(self):
        tmp_dir = test_common.set_tmp_config_dir()
        config_file = "yarss2_v1.2.beta.conf"
        filename = yarss2.util.common.get_resource(config_file, path="tests/data/")
        shutil.copy(filename, tmp_dir)
        self.config = test_common.get_test_config(config_filename=config_file, config_dir=tmp_dir, verify_config=False)

        self.assertEquals(self.config.config._Config__version["format"], 1)
        self.assertEquals(self.config.config._Config__version["file"], 2)

        # Verify that the old values are what we expect
        for key in self.config.config["cookies"].keys():
            self.assertEquals(type(self.config.config["cookies"][key]["value"]), dict)

        # Update the config
        self.config._verify_config()
        config_dict = self.config.config.config

        config_file = "yarss2_v5.conf"
        filename = yarss2.util.common.get_resource(config_file, path="tests/data/")
        shutil.copy(filename, tmp_dir)
        self.config = test_common.get_test_config(config_filename=config_file, config_dir=tmp_dir, verify_config=False)
        config_dict_v5 = self.config.config.config

        # Verify that the 1.2 beta config equals the config updated from earlier versions
        self.assertTrue(yarss2.util.common.dicts_equals(config_dict_v5, config_dict))
