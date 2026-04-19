# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2015 bendikro bro.devel+yarss2@gmail.com
#
# Based on work by:
# Copyright (C) 2009 Camillo Dell'mour <cdellmour@gmail.com>
#
# v2.2.0 maintenance release and WebUI port:
# Copyright (C) 2026 Sam Mahdi
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

from setuptools import find_packages, setup

__plugin_name__ = "YaRSS2"
__author__ = "Bro (original), Sam Mahdi (v2.2.0 maintainer)"
__author_email__ = ""
__version__ = "2.2.0"
__url__ = "https://github.com/TSA3000/deluge-yarss2-webui"
__license__ = "GPLv3"
__description__ = "Yet another RSS 2"
__long_description__ = """
Yet another RSS 2, an RSS plugin for Deluge 2.x. Watches RSS feeds,
filters entries with regex, and auto-adds matching torrents.

v2.2.0 is a security, correctness, and feature release maintained by
Sam Mahdi, based on bendikro's v2.1.5 and Camillo Dell'mour's original.
See CHANGELOG.md and RELEASE_NOTES.md for details.
"""

__pkg_data__ = {__plugin_name__.lower(): ["data/*"]}
packages = find_packages(exclude=["yarss2.tests"])

setup(
    name=__plugin_name__,
    version=__version__,
    description=__description__,
    author=__author__,
    author_email=__author_email__,
    url=__url__,
    license=__license__,
    long_description=__long_description__ if __long_description__ else __description__,
    include_package_data=True,
    packages=packages,
    package_data=__pkg_data__,
    entry_points="""[deluge.plugin.core]
%s = %s:CorePlugin
[deluge.plugin.gtkui]
%s = %s:GtkUIPlugin
[deluge.plugin.web]
%s = %s:WebUIPlugin
[deluge.plugin.gtk3ui]
%s = %s:Gtk3UIPlugin
[yarss2.libpaths]
include = yarss2.include
requests = yarss2.include.requests
dateutil = yarss2.include.dateutil
defusedxml = yarss2.include.defusedxml
beautifulsoup = yarss2.include.beautifulsoup.py3k
atoma = yarss2.include.atoma
html5lib = yarss2.include.html5lib
webencodings = yarss2.include.webencodings
urllib3 = yarss2.include.urllib3.src
certifi = yarss2.include.certifi
""" % ((__plugin_name__, __plugin_name__.lower()) * 4))
