# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2015 bendikro bro.devel+yarss2@gmail.com
#
# Based on work by:
# Copyright (C) 2009 Camillo Dell'mour <cdellmour@gmail.com>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import sys

import pkg_resources

from deluge.plugins.init import PluginInitBase

from yarss2.util import logging

log = logging.getLogger(__name__)


def _expose_vendored_six_as_top_level(egg):
    """Expose the `six.py` bundled inside vendored urllib3 as a top-level module.

    `yarss2/include/urllib3/src/urllib3/packages/six.py` is the only copy of
    `six` shipped in the egg — there is no top-level `six` package. Several
    other vendored libraries (`dateutil`, `html5lib`, ...) do `import six` /
    `from six.moves import ...` at module scope. On a Deluge host that lacks
    a system-installed `six` (typical of the official LinuxServer Deluge
    container on Python 3.12+), those imports raise `ModuleNotFoundError:
    No module named 'six'` as soon as feed parsing touches `dateutil.tz`.

    We exec the bundled six.py under `__name__ == "six"` so that its
    `_SixMetaPathImporter` registers `six.moves.<x>` paths and the standard
    `import six` / `from six import ...` patterns all work. The copy already
    loaded as `urllib3.packages.six` is untouched; the two coexist with
    separate namespace roots.
    """
    if "six" in sys.modules:
        return  # system six already importable, or we already bootstrapped it
    import types
    six_rel = "include/urllib3/src/urllib3/packages/six.py"
    mod = types.ModuleType("six")
    mod.__file__ = "%s/yarss2/%s" % (egg.location, six_rel)
    mod.__path__ = []  # mark as package so `import six.moves` is allowed
    mod.__package__ = "six"
    sys.modules["six"] = mod
    source = pkg_resources.resource_string("yarss2", six_rel)
    code = compile(source, mod.__file__, "exec")
    exec(code, mod.__dict__)


def load_libs():
    egg = pkg_resources.require("YaRSS2")[0]
    for name in egg.get_entry_map("yarss2.libpaths"):
        ep = egg.get_entry_info("yarss2.libpaths", name)
        location = "%s/%s" % (egg.location, ep.module_name.replace(".", "/"))
        if location not in sys.path:
            sys.path.append(location)
        log.debug("Appending to sys.path: '%s'" % location)
    _expose_vendored_six_as_top_level(egg)


class CorePlugin(PluginInitBase):
    def __init__(self, plugin_name):
        load_libs()
        from .core import Core as CorePluginClass
        self._plugin_cls = CorePluginClass
        super(CorePlugin, self).__init__(plugin_name)


class GtkUIPlugin(PluginInitBase):
    def __init__(self, plugin_name):
        load_libs()
        from gtkui.gtkui import GtkUI as GtkUIPluginClass
        self._plugin_cls = GtkUIPluginClass
        super(GtkUIPlugin, self).__init__(plugin_name)


class Gtk3UIPlugin(PluginInitBase):
    def __init__(self, plugin_name):
        load_libs()
        from .gtk3ui.gtkui import GtkUI as GtkUIPluginClass
        self._plugin_cls = GtkUIPluginClass
        super(Gtk3UIPlugin, self).__init__(plugin_name)


class WebUIPlugin(PluginInitBase):
    def __init__(self, plugin_name):
        load_libs()
        from .webui import WebUI as _pluginCls
        self._plugin_cls = _pluginCls
        super(WebUIPlugin, self).__init__(plugin_name)
