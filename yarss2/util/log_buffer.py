# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 Sam Mahdi
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later.
# See LICENSE for more details.
#
"""
In-memory ring buffer for YaRSS2 log messages, exposed to the WebUI.

The backend attaches a `LogBufferHandler` to the `yarss2` logger namespace
on plugin enable. Every log record produced under that namespace (core,
rssfeed_handling, torrent_handling, etc.) is captured in a bounded deque.
Each record gets a monotonic `id` so the WebUI can request "messages since
id N" in a streaming fashion.

The handler is thread-safe because `logging.Handler` guards `emit()` with
an internal RLock.
"""
import logging
import time
from collections import deque
from threading import Lock


class LogBufferHandler(logging.Handler):
    """
    Ring-buffer logging handler. Keeps the most recent `capacity` records
    with monotonically increasing IDs.
    """

    def __init__(self, capacity=1000, level=logging.INFO):
        logging.Handler.__init__(self, level=level)
        self._capacity = capacity
        self._buffer = deque(maxlen=capacity)
        self._next_id = 1
        self._id_lock = Lock()

    def emit(self, record):
        try:
            msg = self.format(record)
        except Exception:
            try:
                msg = record.getMessage()
            except Exception:
                msg = "<unformattable log record>"

        with self._id_lock:
            entry = {
                "id": self._next_id,
                "time": record.created,        # unix timestamp
                "level": record.levelname,     # "INFO" / "WARNING" / etc.
                "logger": record.name,         # e.g. "yarss2.core"
                "message": msg,
            }
            self._next_id += 1
            self._buffer.append(entry)

    def get_since(self, since_id=0, max_messages=500):
        """Return up to `max_messages` entries with id > since_id."""
        # Snapshot under lock to avoid tearing if emit() runs concurrently.
        with self._id_lock:
            snapshot = list(self._buffer)
            next_id = self._next_id
        if since_id <= 0:
            items = snapshot
        else:
            items = [e for e in snapshot if e["id"] > since_id]
        if max_messages and len(items) > max_messages:
            items = items[-max_messages:]
        return {
            "items": items,
            "next_id": next_id,        # hint for the client's next poll
            "capacity": self._capacity,
        }

    def clear(self):
        with self._id_lock:
            self._buffer.clear()


def attach_buffer(logger_name="yarss2", capacity=1000):
    """
    Create a LogBufferHandler and attach it to the given logger namespace.
    Returns the handler. Caller is responsible for detaching on plugin
    disable: `logger.removeHandler(handler)`.
    """
    logger = logging.getLogger(logger_name)
    handler = LogBufferHandler(capacity=capacity)
    # Same format the main Deluge log uses, roughly.
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(handler)
    return handler
