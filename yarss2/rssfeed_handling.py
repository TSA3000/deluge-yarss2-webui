# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2015 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#
import re

import attr

from deluge.error import DelugeError

from yarss2.util import common, http
from yarss2.yarss_config import get_user_agent


# Binary (IEC) and decimal (SI) multipliers, in bytes.
# RSS descriptions in the wild use all of these.
_SIZE_UNITS = {
    "B":   1,
    "KB":  1000,         "KIB": 1024,
    "MB":  1000 ** 2,    "MIB": 1024 ** 2,
    "GB":  1000 ** 3,    "GIB": 1024 ** 3,
    "TB":  1000 ** 4,    "TIB": 1024 ** 4,
}

# "Size: 1.42 GiB" or "Size:800 MB" etc. Case-insensitive.
_SIZE_RE = re.compile(
    r"Size:\s*(?P<size>\d+(?:\.\d+)?)\s*(?P<unit>[KMGT]i?B|B)\b",
    re.IGNORECASE,
)


def _parse_size(string):
    """Parse a 'Size: N UNIT' fragment. Returns (size_in_bytes, pretty_string)
    or (0, None) if nothing usable was found.

    Supports B, KB/KiB, MB/MiB, GB/GiB, TB/TiB — previously only GB and MB
    were recognised, so feeds using IEC units (most trackers) were invisible
    to size-aware matching.
    """
    if not string:
        return 0, None
    match = _SIZE_RE.search(string)
    if not match:
        return 0, None
    size = float(match.group("size"))
    unit = match.group("unit").upper()
    multiplier = _SIZE_UNITS.get(unit)
    if multiplier is None:
        return 0, None
    size_bytes = int(size * multiplier)
    # Preserve the unit as originally written for display
    size_str = "%s %s" % (match.group("size"), match.group("unit"))
    return size_bytes, size_str


def _get_size(item):
    size = []
    if len(item['enclosures']) > 0:
        s = item['enclosures'][0]['length']
        size.append(int(s))

    if "contentlength" in item:
        size_bytes = int(item["contentlength"])
        size.append(int(size_bytes))

    description_content = None
    # Feedparser
    if "summary_detail" in item:
        description_content = item["summary_detail"]["value"]
    # Atom
    elif "description" in item:
        description_content = item["description"]

    if description_content:
        size_bytes, size_str = _parse_size(description_content)
        if size_str and size_bytes:
            size.append((size_bytes, size_str))
    return size


def get_item_download_link(item):
    if len(item["enclosures"]) > 0:
        return item["enclosures"][0]['url']
    return item["link"]


def get_download_size(item):
    return _get_size(item)


def atoma_result_to_dict(atoma_result):

    def item_to_dict(item):
        d = attr.asdict(item)
        if d['pub_date'] is not None:
            dt = d['pub_date']
            if dt.tzinfo is None:
                dt = common.datetime_add_timezone(dt)
            d['published_date'] = dt.isoformat()
            # We must remove datetime.datetime to make the dict encodable by rencode
            del d['pub_date']

        return d

    items = [item_to_dict(item) for item in atoma_result.items if item.title is not None]
    result = {
        'items': items, 'bozo': 0,
        'feed': {
            'ttl': atoma_result.ttl,
            'encoded': atoma_result.content_encoded,
            'link': atoma_result.link,
            'title': atoma_result.title,
            'subtitle': atoma_result.description,
            'language': atoma_result.language,
            'version': atoma_result.version,
        }
    }
    return result


def fetch_and_parse_rssfeed_atom(url_file_stream_or_string, site_cookies_dict=None,
                                 user_agent=None, request_headers=None, timeout=10,
                                 etag=None, last_modified=None):
    result = http.download_file(url_file_stream_or_string, site_cookies_dict=site_cookies_dict,
                                user_agent=user_agent, request_headers=request_headers,
                                timeout=timeout, etag=etag, modified=last_modified)
    import atoma
    atoma.rss.supported_rss_versions = []
    parsed_feeds = {}

    # Propagate cache-validator headers back to the caller so they can be stored
    # on the feed config and sent on the next request as If-None-Match /
    # If-Modified-Since. Missing keys simply mean "server didn't tell us".
    parsed_feeds["etag"] = result.get("etag", "") or ""
    parsed_feeds["last_modified"] = result.get("modified", "") or ""
    parsed_feeds["status"] = result.get("status", 200)

    # HTTP 304 Not Modified — the server told us nothing changed.
    # Return an empty-but-successful result so the scheduler does no work.
    if parsed_feeds["status"] == 304:
        parsed_feeds["items"] = []
        parsed_feeds["feed"] = {}
        parsed_feeds["bozo"] = 0
        parsed_feeds["not_modified"] = True
        parsed_feeds['parser'] = "atoma"
        return parsed_feeds

    try:
        atoma_result = atoma.parse_rss_bytes(result['content'])
        parsed_feeds.update(atoma_result_to_dict(atoma_result))
        parsed_feeds.setdefault("bozo", 0)
    except atoma.FeedXMLError as err:
        readable_body = http.clean_html_body(result['content'])
        parsed_feeds["raw_result"] = readable_body
        parsed_feeds["bozo"] = 1
        parsed_feeds["feed"] = {}
        parsed_feeds["items"] = []
        parsed_feeds["bozo_exception"] = err

    parsed_feeds['parser'] = "atoma"
    return parsed_feeds


def fetch_and_parse_rssfeed_feedparser(url_file_stream_or_string, site_cookies_dict=None,
                                       user_agent=None, request_headers=None, timeout=10,
                                       etag=None, last_modified=None):
    from yarss2.lib.feedparser import api as feedparser

    parsed_feed = feedparser.parse(url_file_stream_or_string, request_headers=request_headers,
                                   agent=user_agent, etag=etag, modified=last_modified,
                                   timeout=10)
    parsed_feed['parser'] = "feedparser"
    # Normalise the cache-validator keys so callers don't have to care which parser ran.
    parsed_feed.setdefault("etag", parsed_feed.get("etag", "") or "")
    parsed_feed.setdefault("last_modified", parsed_feed.get("modified", "") or "")
    return parsed_feed


fetch_and_parse_rssfeed = fetch_and_parse_rssfeed_atom


class RSSFeedHandler(object):

    def __init__(self, log):
        self.log = log

    def get_link(self, item):
        link = None
        if "link" in item:
            link = item['link']
            if len(item['enclosures']) > 0:
                try:
                    link = item['enclosures'][0]['url']
                except AttributeError:
                    pass
        return link

    def get_magnet_link(self, item):
        """
        Get magnet URI from torrent item
        """
        torrent = item['torrent']
        if torrent and torrent['magneturi'] is not None:
            return torrent['magneturi']
        return None

    def get_size(self, item):
        return _get_size(item)

    def get_rssfeed_parsed(self, rssfeed_data, site_cookies_dict=None, user_agent=None):
        """
        rssfeed_data: A dictionary containing rss feed data as stored in the YaRSS2 config.
        site_cookies_dict: A dictionary of cookie values to be used for this rssfeed.
        """
        return_dict = {}
        rssfeeds_dict = {}
        cookie_header = {}
        return_dict["user_agent"] = user_agent

        if site_cookies_dict:
            cookie_header = http.get_cookie_header(site_cookies_dict)
            return_dict["cookie_header"] = cookie_header

        self.log.info("Fetching RSS Feed: '%s' with Cookie: '%s' and User-agent: '%s'." %
                      (rssfeed_data["name"], http.get_cookie_header(cookie_header), user_agent))

        # Will abort after 10 seconds if server doesn't answer
        try:
            # Send cached validators (if any) so the server can respond 304 Not Modified
            # and spare us redundant work + bandwidth.
            etag = rssfeed_data.get("etag", "") or None
            last_modified = rssfeed_data.get("last_modified", "") or None
            parsed_feed = fetch_and_parse_rssfeed(rssfeed_data["url"], user_agent=user_agent,
                                                  request_headers=cookie_header, timeout=10,
                                                  etag=etag, last_modified=last_modified)
        except Exception as e:
            self.log.warning("Exception occured in feedparser: " + str(e))
            self.log.warning("Feedparser was called with url: '%s' using cookies: '%s' and User-agent: '%s'" %
                             (rssfeed_data["url"], http.get_cookie_header(cookie_header), user_agent))
            self.log.warning("Stacktrace:\n" + common.get_exception_string())
            raise DelugeError("Exception occured in feedparser: " + str(e))

        return_dict["raw_result"] = parsed_feed

        # Persist any updated cache validators back onto the feed config so the
        # next fetch can include If-None-Match / If-Modified-Since.
        new_etag = parsed_feed.get("etag", "") or ""
        new_modified = parsed_feed.get("last_modified", "") or ""
        if new_etag:
            rssfeed_data["etag"] = new_etag
        if new_modified:
            rssfeed_data["last_modified"] = new_modified
        return_dict["etag"] = new_etag
        return_dict["last_modified"] = new_modified

        # 304 Not Modified: nothing changed on the server; we're done.
        if parsed_feed.get("not_modified"):
            self.log.info("RSS Feed '%s' not modified since last fetch (HTTP 304)" %
                          rssfeed_data["name"])
            return_dict["not_modified"] = True
            return return_dict

        # Error parsing
        if parsed_feed["bozo"] == 1:
            return_dict["bozo_exception"] = parsed_feed["bozo_exception"]

        # Store ttl value if present
        if "ttl" in parsed_feed["feed"]:
            return_dict["ttl"] = parsed_feed["feed"]["ttl"]
        key = 0
        no_publish_time = False

        for item in parsed_feed['items']:
            # Some RSS feeds do not have a proper timestamp
            magnet = None
            torrent = None

            # Empty item if feed is empty
            if not item:
                continue

            published_date = item.get('published_date', None)
            if published_date is None:
                no_publish_time = True
                return_dict["warning"] = "Published time not available!"

            # Find the link
            link = self.get_link(item)
            magnet = self.get_magnet_link(item)

            # link or enclosures url is magnet
            if link is not None and link.startswith("magnet:"):
                magnet = link
            else:
                torrent = link

            if rssfeed_data.get("prefer_magnet", None) and magnet:
                link = magnet

            rssfeeds_dict[key] = self._new_rssfeeds_dict_item(item['title'], link=link,
                                                              torrent=torrent, magnet=magnet,
                                                              published_date=published_date)

            key += 1

        if no_publish_time:
            self.log.warning("Published time is not available!")
        if key > 0:
            return_dict["items"] = rssfeeds_dict
        return return_dict

    def _new_rssfeeds_dict_item(self, title, link=None, torrent=None, magnet=None,
                                published_date=None, key=None):
        d = {}
        d["title"] = title
        d["link"] = link
        d["matches"] = False
        d["updated"] = ""
        d["magnet"] = magnet
        d["torrent"] = torrent

        if published_date:
            d["updated"] = published_date

        if key is not None:
            d["key"] = key
        return d

    def update_rssfeeds_dict_matching(self, rssfeed_parsed, options):
        """rssfeed_parsed: Dictionary returned by get_rssfeed_parsed_dict
        options, a dictionary with the following keys:
        * "regex_include": str
        * "regex_exclude": str
        * "regex_include_ignorecase": bool
        * "regex_exclude_ignorecase": bool

        Updates the items in rssfeed_parsed
        Return: a dictionary of the matching items only.
        """
        # regex and title are converted from utf-8 unicode to ascii strings before matching
        # This is because the indexes returned by span must be the byte index of the text,
        # because Pango attributes takes the byte index, and not character index.

        matching_items = {}
        p_include = p_exclude = None
        message = None

        # Remove old custom lines
        for key in list(rssfeed_parsed.keys()):
            if rssfeed_parsed[key]["link"] is None:
                del rssfeed_parsed[key]

        if "custom_text_lines" in options and options["custom_text_lines"]:
            if not type(options["custom_text_lines"]) is list:
                self.log.warning("type of custom_text_lines' must be list")
            else:
                for line in options["custom_text_lines"]:
                    key = common.get_new_dict_key(rssfeed_parsed, string_key=False)
                    rssfeed_parsed[key] = self._new_rssfeeds_dict_item(line, key=key)

        if options["regex_include"] is not None and options["regex_include"] != "":
            flags = re.IGNORECASE if options["regex_include_ignorecase"] else 0
            try:
                regex = options["regex_include"].encode("utf-8")
                p_include = re.compile(regex, flags)
            except Exception as e:
                self.log.warning("Regex compile error:" + str(e))
                message = "Regex: %s" % e
                p_include = None

        if options["regex_exclude"] is not None and options["regex_exclude"] != "":
            flags = re.IGNORECASE if options["regex_exclude_ignorecase"] else 0
            try:
                regex = options["regex_exclude"].encode("utf-8")
                p_exclude = re.compile(regex, flags)
            except Exception as e:
                self.log.warning("Regex compile error:" + str(e))
                message = "Regex: %s" % e
                p_exclude = None

        for key in rssfeed_parsed.keys():
            item = rssfeed_parsed[key]
            title = item["title"].encode("utf-8")

            if "regex_exclude_match" in item:
                del item["regex_exclude_match"]
            if "regex_include_match" in item:
                del item["regex_include_match"]

            item["matches"] = False
            if p_include:
                m = p_include.search(title)
                if m:
                    item["matches"] = True
                    item["regex_include_match"] = m.span()
            if p_exclude:
                m = p_exclude.search(title)
                if m:
                    item["matches"] = False
                    item["regex_exclude_match"] = m.span()
            if item["matches"]:
                matching_items[key] = rssfeed_parsed[key]

        return matching_items, message

    def fetch_feed_torrents(self, config, rssfeed_key, subscription_key=None):
        """Called to fetch torrents for a feed
        If rssfeed_key is not None, all subscriptions linked to that RSS Feed
        will be run.
        If rssfeed_key is None, only the subscription with key == subscription_key
        will be run
        """
        fetch_data = {}
        fetch_data["matching_torrents"] = []
        fetch_data["rssfeed_items"] = None

        if rssfeed_key is None:
            if subscription_key is None:
                self.log.warning("rssfeed_key and subscription_key cannot both be None")
                return fetch_data
            rssfeed_key = config["subscriptions"][subscription_key]["rssfeed_key"]
        else:
            # RSS Feed is not enabled
            if config["rssfeeds"][rssfeed_key]["active"] is False:
                return fetch_data

        rssfeed_data = config["rssfeeds"][rssfeed_key]
        fetch_data["site_cookies_dict"] = http.get_matching_cookies_dict(config["cookies"], rssfeed_data["site"])
        fetch_data["user_agent"] = get_user_agent(rssfeed_data=rssfeed_data)

        self.log.info("Update handler executed on RSS Feed '%s (%s)' (Update interval %d min)" %
                      (rssfeed_data["name"], rssfeed_data["site"], rssfeed_data["update_interval"]))

        for key in config["subscriptions"].keys():
            # subscription_key is given, only that subscription will be run
            if subscription_key is not None and subscription_key != key:
                continue
            subscription_data = config["subscriptions"][key]
            if subscription_data["rssfeed_key"] == rssfeed_key and subscription_data["active"] is True:
                self.fetch_feed(subscription_data, rssfeed_data, fetch_data)

        if subscription_key is None:
            # Update last_update value of the rssfeed only when rssfeed is run by the timer,
            # not when a subscription is run manually by the user.
            # Don't need microseconds. Remove because it requires changes to the GUI to not display them
            dt = common.get_current_date().replace(microsecond=0)
            rssfeed_data["last_update"] = dt.isoformat()
        return fetch_data

    def handle_ttl(self, rssfeed_data, rssfeed_parsed, fetch_data):
        if rssfeed_data["obey_ttl"] is False:
            return
        if "ttl" in rssfeed_parsed:
            # Value is already TTL, so ignore
            try:
                ttl = int(rssfeed_parsed["ttl"])
                if rssfeed_data["update_interval"] == ttl:
                    return
                # Verify that the TTL value is actually an integer (just in case)
                # At least 1 minute, and not more than one year
                if ttl > 0 and ttl < 524160:
                    fetch_data["ttl"] = ttl
                else:
                    self.log.warning("TTL value is invalid: %d" % ttl)
            except (ValueError, TypeError):
                self.log.warning("Failed to convert TTL value '%s' to int!" % rssfeed_parsed["ttl"])
        else:
            self.log.warning("RSS Feed '%s' should obey TTL, but feed has no TTL value." %
                             rssfeed_data["name"])
            self.log.info("Obey TTL option set to False")
            rssfeed_data["obey_ttl"] = False

    def fetch_feed(self, subscription_data, rssfeed_data, fetch_data):
        """Search a feed with config 'subscription_data'"""
        self.log.info("Fetching subscription '%s'." % subscription_data["name"])

        # Feed has not yet been fetched.
        if fetch_data["rssfeed_items"] is None:
            rssfeed_parsed = self.get_rssfeed_parsed(rssfeed_data, site_cookies_dict=fetch_data["site_cookies_dict"],
                                                     user_agent=fetch_data["user_agent"])
            if rssfeed_parsed is None:
                return
            if "bozo_exception" in rssfeed_parsed:
                self.log.warning("bozo_exception when parsing rssfeed: %s" % str(rssfeed_parsed["bozo_exception"]))
            if "items" in rssfeed_parsed:
                fetch_data["rssfeed_items"] = rssfeed_parsed["items"]
                self.handle_ttl(rssfeed_data, rssfeed_parsed, fetch_data)
            elif rssfeed_parsed.get("not_modified"):
                # HTTP 304: feed body unchanged since last fetch. No new items
                # to evaluate. Not an error — just silently skip this subscription.
                return
            else:
                self.log.warning("No items retrieved")
                return
        # Remove the custom text lines before matching (not strictly necessary though,
        # but they are only for testing in the DialogSubscription)
        options = subscription_data.copy()
        del options["custom_text_lines"]
        matches, message = self.update_rssfeeds_dict_matching(fetch_data["rssfeed_items"], options=options)
        self.log.info("%d items in feed, %d matches the filter." %
                      (len(fetch_data["rssfeed_items"]), len(matches.keys())))
        last_match_dt = common.isodate_to_datetime(subscription_data["last_match"])

        for key in list(matches.keys()):
            # Discard match only if timestamp is available,
            # and the timestamp is older or equal to the last matching timestamp
            matched_updated = common.isodate_to_datetime(matches[key]["updated"])
            if matched_updated and last_match_dt >= matched_updated:
                if subscription_data["ignore_timestamp"] is True:
                    self.log.info("Old timestamp: '%s', but ignore option is enabled so add torrent anyways."
                                  % matches[key]["title"])
                else:
                    self.log.info("Not adding because of old timestamp: '%s'" % matches[key]["title"])
                    del matches[key]
                    continue
            fetch_data["matching_torrents"].append({"title": matches[key]["title"],
                                                    "link": matches[key]["link"],
                                                    "updated_datetime": matched_updated,
                                                    "site_cookies_dict": fetch_data["site_cookies_dict"],
                                                    "user_agent": fetch_data["user_agent"],
                                                    "referrer": rssfeed_data["url"],
                                                    "verify_tls": rssfeed_data.get("verify_tls", True),
                                                    "subscription_data": subscription_data})
