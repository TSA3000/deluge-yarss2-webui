# -*- coding: utf-8 -*-
#
# Tests covering the v2.2.0 / config-v9 fixes:
#
#   1. Cookie matching uses proper hostname comparison (not substring find).
#   2. `_parse_size` understands B, KB/KiB, MB/MiB, GB/GiB, TB/TiB.
#   3. Email-notification send loop uses its own loop variable (not a leaked
#      one from the surrounding scope).
#   4. ETag / Last-Modified cache validators are stored on the feed config
#      after a successful fetch.
#
# These behaviours previously had no coverage — which is exactly how each
# of the underlying bugs survived into v2.1.5.
#

from twisted.trial import unittest

from yarss2 import rssfeed_handling
from yarss2.util import http


class CookieDomainMatchingTestCase(unittest.TestCase):
    """Cookie matching must align on DNS domain boundaries, not substrings."""

    def _cookie(self, site, active=True):
        return {"0": {"active": active, "site": site, "value": {"sid": "abc"}}}

    def test_exact_hostname_matches(self):
        cookies = self._cookie("example.com")
        self.assertEqual(
            http.get_matching_cookies_dict(cookies, "https://example.com/feed"),
            {"sid": "abc"},
        )

    def test_subdomain_matches(self):
        cookies = self._cookie("example.com")
        self.assertEqual(
            http.get_matching_cookies_dict(cookies, "https://rss.example.com/feed"),
            {"sid": "abc"},
        )

    def test_leading_dot_domain_matches(self):
        cookies = self._cookie(".example.com")
        self.assertEqual(
            http.get_matching_cookies_dict(cookies, "https://rss.example.com/feed"),
            {"sid": "abc"},
        )

    def test_prefix_attack_does_not_match(self):
        # OLD (buggy) substring behaviour: 'example.com' would match
        # 'notexample.com' because the string 'example.com' appears in it.
        cookies = self._cookie("example.com")
        self.assertEqual(
            http.get_matching_cookies_dict(cookies, "https://notexample.com/feed"),
            {},
        )

    def test_suffix_attack_does_not_match(self):
        # Attacker-controlled subdomain of an unrelated tld that happens to
        # contain the legit host as a substring.
        cookies = self._cookie("example.com")
        self.assertEqual(
            http.get_matching_cookies_dict(cookies, "https://example.com.evil.tld/feed"),
            {},
        )

    def test_inactive_cookie_ignored(self):
        cookies = self._cookie("example.com", active=False)
        self.assertEqual(
            http.get_matching_cookies_dict(cookies, "https://example.com/feed"),
            {},
        )

    def test_bare_host_cookie_site_still_works(self):
        # Users commonly configure the cookie site as a bare host, not a URL.
        cookies = self._cookie("tracker.example.com")
        self.assertEqual(
            http.get_matching_cookies_dict(cookies, "https://tracker.example.com/feed?x=1"),
            {"sid": "abc"},
        )


class ParseSizeTestCase(unittest.TestCase):
    """_parse_size must handle every unit commonly seen in tracker RSS feeds."""

    def _bytes(self, s):
        return rssfeed_handling._parse_size(s)[0]

    def _str(self, s):
        return rssfeed_handling._parse_size(s)[1]

    def test_returns_zero_for_nothing_useful(self):
        self.assertEqual(rssfeed_handling._parse_size(""), (0, None))
        self.assertEqual(rssfeed_handling._parse_size("no size here"), (0, None))

    def test_decimal_units(self):
        self.assertEqual(self._bytes("Size: 1 KB"), 1000)
        self.assertEqual(self._bytes("Size: 1 MB"), 1000 ** 2)
        self.assertEqual(self._bytes("Size: 1 GB"), 1000 ** 3)
        self.assertEqual(self._bytes("Size: 1 TB"), 1000 ** 4)

    def test_binary_units(self):
        self.assertEqual(self._bytes("Size: 1 KiB"), 1024)
        self.assertEqual(self._bytes("Size: 1 MiB"), 1024 ** 2)
        self.assertEqual(self._bytes("Size: 1 GiB"), 1024 ** 3)
        self.assertEqual(self._bytes("Size: 1 TiB"), 1024 ** 4)

    def test_fractional_value(self):
        # 1.5 GiB = 1.5 * 2^30
        self.assertEqual(self._bytes("Size: 1.5 GiB"), int(1.5 * 1024 ** 3))

    def test_case_insensitive(self):
        self.assertEqual(self._bytes("size: 2 gib"), 2 * 1024 ** 3)
        self.assertEqual(self._bytes("SIZE:3MB"), 3 * 1000 ** 2)

    def test_whitespace_optional(self):
        self.assertEqual(self._bytes("Size:800MB"), 800 * 1000 ** 2)
        self.assertEqual(self._bytes("Size:   42 TiB"), 42 * 1024 ** 4)

    def test_display_string_preserves_input(self):
        self.assertEqual(self._str("Size: 1.42 GiB"), "1.42 GiB")
        self.assertEqual(self._str("Size: 800 MB"), "800 MB")

    def test_previously_unsupported_units_now_work(self):
        # Pre-v9 only GB|MB were recognised. These used to return (0, None).
        self.assertGreater(self._bytes("Size: 700 MiB"), 0)
        self.assertGreater(self._bytes("Size: 2 TiB"), 0)


class EmailNotificationScopeTestCase(unittest.TestCase):
    """The email send loop must use its own loop variable, not one leaked
    from the 'collect notification keys' loop above it.

    The bug: when a single run produced matches for multiple subscriptions
    and those subscriptions used *different* email message keys, the outer
    loop ended up sending every email with the subscription_data / torrent
    list that belonged to whichever key happened to be last in the previous
    inner loop — not the one the current email was addressed to.

    We reproduce that scenario by stubbing `send_torrent_email` and checking
    that each call receives the matching (email_key, subscription, torrents).
    """

    def test_each_email_gets_its_own_payload(self):
        from yarss2 import torrent_handling as th

        calls = []

        def fake_send(email_config, message, subscription_data=None,
                      torrent_name_list=None, deferred=True):
            calls.append({
                "message": message["name"],
                "subscription": subscription_data["name"],
                "torrents": list(torrent_name_list),
            })

        # Monkey-patch the symbol actually used inside add_torrents
        original = th.send_torrent_email
        th.send_torrent_email = fake_send
        try:
            # Stub the underlying add_torrent so we don't touch Deluge.
            class StubDownload(object):
                success = True
            handler = th.TorrentHandler(logger=_NullLog())
            handler.add_torrent = lambda info: StubDownload()

            sub_a = _make_subscription("SubA", email_keys=["msgA"])
            sub_b = _make_subscription("SubB", email_keys=["msgB"])

            torrent_list = [
                _make_torrent_match("t1", sub_a),
                _make_torrent_match("t2", sub_b),
            ]

            config = {
                "email_configurations": {"send_email_on_torrent_events": True},
                "email_messages": {
                    "msgA": {"name": "Message A", "active": True},
                    "msgB": {"name": "Message B", "active": True},
                },
            }

            handler.add_torrents(save_subscription_func=lambda **kw: None,
                                 torrent_list=torrent_list,
                                 config=config)
        finally:
            th.send_torrent_email = original

        # We expect one send per active message, each with the correct
        # subscription name and torrent title.
        by_message = {c["message"]: c for c in calls}
        self.assertEqual(set(by_message), {"Message A", "Message B"})
        self.assertEqual(by_message["Message A"]["subscription"], "SubA")
        self.assertEqual(by_message["Message A"]["torrents"], ["t1"])
        self.assertEqual(by_message["Message B"]["subscription"], "SubB")
        self.assertEqual(by_message["Message B"]["torrents"], ["t2"])


class EtagCachePersistenceTestCase(unittest.TestCase):
    """After a successful fetch that surfaces ETag / Last-Modified headers,
    the feed config must be updated so the next fetch can send
    If-None-Match / If-Modified-Since."""

    def test_feed_config_receives_cache_headers(self):
        rssfeed_data = {
            "name": "T", "url": "http://example.invalid/feed",
            "site": "example.invalid",
            "obey_ttl": False, "etag": "", "last_modified": "",
        }

        # Patch the module-level fetcher so no network is touched.
        fake_result = {
            "items": [], "bozo": 0, "feed": {},
            "etag": 'W/"abc123"',
            "last_modified": "Wed, 01 Jan 2025 00:00:00 GMT",
            "status": 200,
            "parser": "atoma",
        }
        original = rssfeed_handling.fetch_and_parse_rssfeed
        rssfeed_handling.fetch_and_parse_rssfeed = lambda *a, **kw: fake_result
        try:
            handler = rssfeed_handling.RSSFeedHandler(_NullLog())
            handler.get_rssfeed_parsed(rssfeed_data)
        finally:
            rssfeed_handling.fetch_and_parse_rssfeed = original

        self.assertEqual(rssfeed_data["etag"], 'W/"abc123"')
        self.assertEqual(rssfeed_data["last_modified"],
                         "Wed, 01 Jan 2025 00:00:00 GMT")

    def test_304_response_is_fast_path(self):
        rssfeed_data = {
            "name": "T", "url": "http://example.invalid/feed",
            "site": "example.invalid",
            "obey_ttl": False, "etag": 'W/"old"', "last_modified": "",
        }
        fake_result = {
            "items": [], "bozo": 0, "feed": {},
            "etag": 'W/"old"',  # unchanged
            "last_modified": "", "status": 304,
            "not_modified": True,
            "parser": "atoma",
        }
        original = rssfeed_handling.fetch_and_parse_rssfeed
        rssfeed_handling.fetch_and_parse_rssfeed = lambda *a, **kw: fake_result
        try:
            handler = rssfeed_handling.RSSFeedHandler(_NullLog())
            result = handler.get_rssfeed_parsed(rssfeed_data)
        finally:
            rssfeed_handling.fetch_and_parse_rssfeed = original

        self.assertTrue(result.get("not_modified"))
        # ETag is preserved on the feed config for the next request.
        self.assertEqual(rssfeed_data["etag"], 'W/"old"')


# --- Test helpers ----------------------------------------------------------

class _NullLog(object):
    def info(self, *a, **kw): pass
    def warn(self, *a, **kw): pass
    def warning(self, *a, **kw): pass
    def error(self, *a, **kw): pass
    def debug(self, *a, **kw): pass


def _make_subscription(name, email_keys):
    return {
        "name": name,
        "last_match": "",
        "email_notifications": {
            k: {"on_torrent_added": True} for k in email_keys
        },
        # Minimal fields the add_torrents path pokes at:
        "move_completed": "", "download_location": "",
        "add_torrents_in_paused_state": "Default",
        "auto_managed": "Default",
        "sequential_download": "Default",
        "prioritize_first_last_pieces": "Default",
        "max_download_speed": -2, "max_upload_speed": -2,
        "max_connections": -2, "max_upload_slots": -2,
    }


def _make_torrent_match(title, subscription_data):
    return {
        "title": title,
        "link": "http://example.invalid/%s.torrent" % title,
        "updated_datetime": None,
        "site_cookies_dict": {},
        "subscription_data": subscription_data,
    }
