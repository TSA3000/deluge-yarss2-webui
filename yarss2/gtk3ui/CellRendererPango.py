# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2019 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

from .common import GObject, Gtk, Pango, PangoCairo


class CustomAttribute(GObject.GObject, object):

    def __init__(self, attributes_dict=None):
        super(CustomAttribute, self).__init__()
        self.attributes_dict = attributes_dict

    def __str__(self):
        return str(self.attributes_dict)


GObject.type_register(CustomAttribute)


class CellRendererPango(Gtk.CellRendererText):

    __gproperties__ = {
        "custom": (CustomAttribute, "custom", "custom", GObject.ParamFlags.READWRITE),
    }

    property_names = __gproperties__.keys()

    def __init__(self):
        GObject.GObject.__init__(self)
        self.include_color_string = "#5acf36"  # Green
        self.exclude_color_string = "#f31010"  # Red

    def __getattr__(self, name):
        try:
            return self.get_property(name)
        except TypeError:
            raise AttributeError

    def __setattr__(self, name, value):
        try:
            self.set_property(name, value)
        except TypeError:
            self.__dict__[name] = value

    def do_get_property(self, property):
        if property.name not in self.property_names:
            raise TypeError('No property named %s' % (property.name,))
        return self.__dict__[property.name]

    def do_set_property(self, property, value):
        if property.name not in self.property_names:
            raise TypeError('No property named %s' % (property.name,))
        self.__dict__[property.name] = value

    def get_text(self):
        value = self.get_property('text')
        return value

    def get_layout(self, widget):
        '''Gets the Pango layout used in the cell in a TreeView widget.'''
        layout = Pango.Layout(widget.get_pango_context())
        layout.set_width(-1)  # Do not wrap text.
        return layout

    def do_render(self, window, widget, background_area, cell_area, expose_area, flags=None):
        """
        Args:
            window (cairo.Context)
            widget (gi.overrides.Gtk.TreeView)
            background_area (gi.repository.Gdk.Rectangle)
            cell_area (gi.repository.Gdk.Rectangle)
            expose_area (gi.repository.Gtk.CellRendererState)
        """
        cairo_context = window
        layout = self.get_layout(widget)
        custom_attr = self.get_property("custom")
        markup = self.get_text()

        def rgb_to_hex(rgb):
            return '#%02x%02x%02x' % rgb

        if custom_attr and custom_attr.attributes_dict:
            attributes_dict = custom_attr.attributes_dict

            def markup_text(txt, start, end, color):
                markuped = txt[0:start]
                markuped += '<span background="%s"><b>%s</b></span>' % (color, txt[start:end])
                markuped += txt[end:]
                return markuped

            if "regex_exclude_match" in attributes_dict:
                start, end = attributes_dict["regex_exclude_match"]
                color = self.exclude_color_string
                markup = markup_text(markup, start, end, color)

            elif "regex_include_match" in attributes_dict:
                start, end = attributes_dict["regex_include_match"]
                color = self.include_color_string
                markup = markup_text(markup, start, end, color)

        layout.set_markup(markup)

        # Vertically align the text
        cell_area.y += 4
        cell_area.x += 1

        cairo_context.move_to(cell_area.x, cell_area.y)
        PangoCairo.show_layout(cairo_context, layout)

    def do_get_size(self, widget, cell_area=None):
        return Gtk.CellRendererText.do_get_size(self, widget, cell_area)


GObject.type_register(CellRendererPango)
