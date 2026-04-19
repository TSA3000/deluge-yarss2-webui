# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2015 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import traceback

import twisted.internet.defer as defer
from twisted.internet import threads
from twisted.internet.task import LoopingCall
from twisted.python.failure import Failure

import deluge.component as component

from yarss2.rssfeed_handling import RSSFeedHandler
from yarss2.torrent_handling import TorrentHandler
from yarss2.yarss_config import YARSSConfigChangedEvent


class RSSFeedScheduler(object):
    """Handles scheduling the RSS Feed fetches."""

    def __init__(self, config, logger):
        self.yarss_config = config
        self.rssfeed_timers = {}
        concurrent_max = 1
        try:
            concurrent_max = int(
                config.get_config().get("general", {}).get("max_concurrent_feeds", 1)
            )
            if concurrent_max < 1:
                concurrent_max = 1
        except (AttributeError, TypeError, ValueError):
            concurrent_max = 1
        self.run_queue = RSSFeedRunQueue(concurrent_max=concurrent_max)
        self.log = logger
        self.rssfeedhandler = RSSFeedHandler(logger)
        self.torrent_handler = TorrentHandler(logger)
        # To make it possible to disable adding torrents in testing
        self.add_torrents_func = self.torrent_handler.add_torrents

    def enable_timers(self):
        """Creates the LoopingCall timers, one for each RSS Feed"""
        config = self.yarss_config.get_config()
        for key in config["rssfeeds"]:
            rssfeed = config["rssfeeds"][key]
            self.set_timer(rssfeed["key"], rssfeed['update_interval'], rssfeed["update_on_startup"])
            self.log.info("Scheduled RSS Feed '%s' with interval %s" %
                          (rssfeed["name"], rssfeed["update_interval"]))

    def disable_timers(self):
        for key in list(self.rssfeed_timers.keys()):
            self.rssfeed_timers[key]["timer"].stop()
            del self.rssfeed_timers[key]

    def set_timer(self, key, interval, update_on_startup=False):
        """Schedule a timer for the specified interval."""
        try:
            interval = int(interval)
        except ValueError:
            self.log.error("Failed to convert interval '%s' to int!" % str(interval))
            return False
        # Already exists, so reschedule
        if key in self.rssfeed_timers:
            try:
                self.rssfeed_timers[key]["timer"].stop()
            except AssertionError as e:
                self.log.warning("AssertionError:", e)
                return False
            self.rssfeed_timers[key]["update_interval"] = interval
        else:
            # New timer
            # Second argument, the rssfeedkey is passed as argument to the callback method
            timer = LoopingCall(self.queue_rssfeed_update, key)
            self.rssfeed_timers[key] = {"timer": timer, "update_interval": interval}
        self.rssfeed_timers[key]["timer"].start(interval * 60, now=update_on_startup)  # Multiply to get seconds
        return True

    def delete_timer(self, key):
        """Delete timer with the specified key."""
        if key not in self.rssfeed_timers:
            self.log.warning("Cannot delete timer. No timer with key %s" % key)
            return False
        self.rssfeed_timers[key]["timer"].stop()
        del self.rssfeed_timers[key]
        return True

    def rssfeed_update_handler_safe(self, rssfeed_key=None, subscription_key=None):
        """
        This function is called by the LoopingCall, and should avoid passing any
        raised exceptions back to the loopingcall. This is to make sure the loopingcall
        doesn't stop.
        """
        try:
            return self.rssfeed_update_handler(rssfeed_key=rssfeed_key, subscription_key=subscription_key)
        except:  # noqa: E722 do not use bare 'except'
            traceback.print_exc()
            exc_str = traceback.format_exc()
            self.log.warning("An exception was thrown by the RSS update handler. Please report this bug!\n%s" % exc_str)

    def rssfeed_update_handler(self, rssfeed_key=None, subscription_key=None):
        """Goes through all the feeds and runs the active ones.
        Multiple subscriptions on one RSS Feed will download the RSS feed page only once
        """
        if subscription_key:
            self.log.info("Manually running Subscription '%s'" %
                          (self.yarss_config.get_config()["subscriptions"][subscription_key]["name"]))
        elif rssfeed_key:
            if self.yarss_config.get_config()["rssfeeds"][rssfeed_key]["active"] is False:
                return

        fetch_result = self.rssfeedhandler.fetch_feed_torrents(self.yarss_config.get_config(), rssfeed_key,
                                                               subscription_key=subscription_key)
        matching_torrents = fetch_result["matching_torrents"]
        # Fetching the torrent files. Do this slow task in non-main thread.
        for torrent in matching_torrents:
            torrent["torrent_download"] = self.torrent_handler.get_torrent(torrent)

        # Update TTL value?
        if "ttl" in fetch_result:
            # Subscription is run directly. Get RSS Feed key
            if not rssfeed_key:
                rssfeed_key = self.yarss_config.get_config()["subscriptions"][subscription_key]["rssfeed_key"]
            self.log.info("Rescheduling RSS Feed '%s' with interval '%s' according to TTL." %
                          (self.yarss_config.get_config()["rssfeeds"][rssfeed_key]["name"], fetch_result["ttl"]))
            rssfeed = self.yarss_config.get_config()["rssfeeds"][rssfeed_key]
            # Set new interval in config
            rssfeed["update_interval"] = fetch_result["ttl"]
            # Reschedule timer
            self.set_timer(rssfeed_key, fetch_result["ttl"], rssfeed["update_on_startup"])
        # Send YARSSConfigChangedEvent to GUI with updated config.
        try:
            # Tests throws KeyError for EventManager when running this method, so wrap this in try/except
            component.get("EventManager").emit(YARSSConfigChangedEvent(self.yarss_config.get_config()))
        except KeyError:
            pass

        def save_subscription_func(subscription_data):
            self.yarss_config.generic_save_config("subscriptions", data_dict=subscription_data)

        return (self.add_torrents_func, save_subscription_func,
                fetch_result["matching_torrents"], self.yarss_config.get_config())

    def add_torrents_callback(self, args):
        """
        Called with the results from rssfeed_update_handler
        add_torrents_func must be called on the main thread

        """
        if args is None:
            return
        add_torrents_func, save_subscription_func, matching_torrents, config = args
        add_torrents_func(save_subscription_func, matching_torrents, config)

    def queue_rssfeed_update(self, *args, **kwargs):
        d = self.run_queue.push(self.rssfeed_update_handler_safe, *args, **kwargs)
        d.addCallback(self.add_torrents_callback)
        return d


class RSSFeedRunQueue(object):
    """Runs functions in separate threads. If a job is already running,
    jobs pushed are queued until the running job has finished.

    `concurrent_max` controls how many jobs may run in parallel. This is read
    from the `general.max_concurrent_feeds` config option (default 1).
    """
    def __init__(self, concurrent_max=1):
        self.concurrent_max = concurrent_max
        self._running = 0
        self._queued = []

    def push(self, f, *args, **kwargs):
        """Push job to queue"""
        if self._running < self.concurrent_max:
            return self._run(f, args, kwargs)
        d = defer.Deferred()
        self._queued.append((f, args, kwargs, d))
        return d

    def _run(self, f, args, kwargs):
        """Run function in separate thread"""
        self._running += 1
        deferred = threads.deferToThread(f, *args, **kwargs)
        deferred.addBoth(self._try_queued)
        return deferred

    def _try_queued(self, r):
        """Execute next job in queue if it exists"""
        self._running -= 1
        if self._running < self.concurrent_max and self._queued:
            f, args, kwargs, d = self._queued.pop(0)
            new_d = self._run(f, args, kwargs)
            new_d.chainDeferred(d)
        if isinstance(r, Failure):
            r.trap()
        return r
