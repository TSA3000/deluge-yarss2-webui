# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2015 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#
from __future__ import print_function

import datetime
import os
import sys

import pkg_resources

PY2 = sys.version_info.major == 2
PY3 = sys.version_info.major == 3


def get_version():
    """
    Returns the program version from the egg metadata

    :returns: the version of Deluge
    :rtype: string

    """
    return pkg_resources.require("YaRSS2")[0].version


def is_running_from_egg():
    egg = pkg_resources.require("YaRSS2")[0]
    return egg.location.endswith(".egg")


def get_deluge_version():
    import deluge.common
    return deluge.common.get_version()


def get_resource(filename, path="data"):
    if path:
        filename = os.path.join(path, filename)
    return pkg_resources.resource_filename("yarss2", filename)


def get_default_date():
    return datetime_add_timezone(datetime.datetime(datetime.MINYEAR, 1, 1, 0, 0, 0, 0))


def get_current_date():
    return datetime_add_timezone(datetime.datetime.now())


def get_current_date_in_isoformat():
    return get_current_date().strftime("%Y-%m-%dT%H:%M:%S")


def datetime_ensure_timezone(dt):
    if dt.tzinfo is None:
        dt = datetime_add_timezone(dt)
    return dt


def datetime_add_timezone(dt, tzinfo=None):
    from dateutil.tz import tzutc
    if tzinfo is None:
        tzinfo = tzutc()
    return dt.replace(tzinfo=tzinfo)


def isodate_to_datetime(date_in_isoformat):
    """
    Args:
        date_in_isoformat (str): The date in iso format

    Returns:
        datetime.datetime: The datetime object converted from date_in_isoformat

    """
    from dateutil import parser as dateutil_parser
    try:
        dt = dateutil_parser.parse(date_in_isoformat)
        return datetime_add_timezone(dt)
    except ValueError as err:
        from yarss2.util import logging
        log = logging.getLogger(__name__)
        log.warning("isodate_to_datetime error:", err)
        return get_default_date()


def get_new_dict_key(dictionary, string_key=True):
    """Returns the first unused key in the dictionary.
    string_key: if True, use strings as key, else use int
    """
    key = 0
    conv = int
    if string_key:
        conv = str
    while conv(key) in dictionary:
        key += 1
    return str(key) if string_key else key


def get_value_in_selected_row(treeview, store, column_index=0):
    """Helper to get the value at index 'index_column' of the selected element
    in the given treeview.
    return None of no item is selected.
    """
    tree, tree_id = treeview.get_selection().get_selected()
    if tree_id:
        value = store.get_value(tree_id, column_index)
        return value
    return None


def write_to_file(filepath, content):
    """Used for debugging"""
    if "%d" in filepath:
        count = 0
        while os.path.isfile(filepath % count):
            count += 1
        filepath = filepath % count
    local_file = open(filepath, "w")
    local_file.write(content)
    local_file.close()


def read_file(filepath):
    if not os.path.isfile(filepath):
        return None
    f = open(filepath, "rb")
    content = f.read()
    return content


def method_name():
    return sys._getframe(3).f_code.co_name


def filename(level=3):
    fname = sys._getframe(level).f_code.co_filename
    fname = os.path.splitext(os.path.basename(fname))[0]
    return fname


def linenumber(level=3):
    return sys._getframe(level).f_lineno


def get_exception_string():
    import traceback
    exc_type, exc_value, exc_traceback = sys.exc_info()
    lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    return ''.join('!! ' + line for line in lines)


def dicts_equals(dict1, dict2, debug=False):
    """Compares two dictionaries, checking that they have the same key/values"""
    ret = True
    if not (type(dict1) is dict and type(dict2) is dict):
        print("dicts_equals: Both arguments are not dictionaries!")
        return False

    key_diff = set(dict1.keys()) - set(dict2.keys())
    if key_diff:
        if debug:
            print("dicts_equals: Keys differ:", key_diff)
        return False
    for key in dict1.keys():
        if type(dict1[key]) is dict and type(dict2[key]) is dict:
            if not dicts_equals(dict1[key], dict2[key], debug=debug):
                ret = False
        else:
            # Compare values
            if dict1[key] != dict2[key]:
                if debug:
                    print("Value for key '%s' differs. Value1: '%s', Value2: '%s'" % (key, dict1[key], dict2[key]))
                ret = False
    return ret


def is_hidden(filepath):
    def has_hidden_attribute(filepath):
        import win32api
        import win32con
        try:
            attribute = win32api.GetFileAttributes(filepath)
            return attribute & (win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM)
        except (AttributeError, AssertionError):
            return False

    name = os.path.basename(os.path.abspath(filepath))
    # Windows
    if os.name == 'nt':
        return has_hidden_attribute(filepath)
    return name.startswith('.')


def get_completion_paths(args):
    """
    Takes a path value and returns the available completions.
    If the path_value is a valid path, return all sub-directories.
    If the path_value is not a valid path, remove the basename from the
    path and return all sub-directories of path that start with basename.

    :param args: options
    :type args: dict
    :returns: the args argument containing the available completions for the completion_text
    :rtype: list

    """
    args["paths"] = []
    path_value = args["completion_text"]
    hidden_files = args["show_hidden_files"]

    def get_subdirs(dirname):
        try:
            if PY2:
                return os.walk(dirname).__next__[1]
            else:
                return next(os.walk(dirname))[1]
        except StopIteration:
            # Invalid dirname
            return []

    dirname = os.path.dirname(path_value)
    basename = os.path.basename(path_value)

    dirs = get_subdirs(dirname)
    # No completions available
    if not dirs:
        return args

    # path_value ends with path separator so
    # we only want all the subdirectories
    if not basename:
        # Lets remove hidden files
        if not hidden_files:
            old_dirs = dirs
            dirs = []
            for d in old_dirs:
                if not is_hidden(os.path.join(dirname, d)):
                    dirs.append(d)
    matching_dirs = []
    for s in dirs:
        if s.startswith(basename):
            p = os.path.join(dirname, s)
            if not p.endswith(os.path.sep):
                p += os.path.sep
            matching_dirs.append(p)

    args["paths"] = sorted(matching_dirs)
    return args


class GeneralSubsConf:
    """General subscription config"""
    DISABLED = u"False"
    ENABLED = u"True"
    DEFAULT = u"Default"

    def __init__(self):
        pass

    def get_boolean(self, value):
        """input value should not be GeneralSubsConf.DEFAULT"""
        return False if value == GeneralSubsConf.DISABLED else True

    def bool_to_value(self, enabled, default):
        if default:
            return GeneralSubsConf.DEFAULT
        elif enabled:
            return GeneralSubsConf.ENABLED
        else:
            return GeneralSubsConf.DISABLED


class TorrentDownload(dict):
    def __init__(self, d={}):
        self["filedump"] = None
        self["error_msg"] = None
        self["torrent_id"] = None
        self["success"] = True
        self["url"] = None
        self["is_magnet"] = False
        self["cookies_dict"] = None
        self.update(d)

    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, name, value):
        self[name] = value

    def set_error(self, error_msg):
        self["error_msg"] = error_msg
        self["success"] = False

    def to_dict(self):
        return self.copy()
