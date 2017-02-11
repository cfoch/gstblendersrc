# -*- coding: utf-8 -*-
# GstBlenderSrc
# Copyright (c) 2017, Fabian Orccon <cfoch.fabian@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
import logging
import sys
sys.argv = []

import bpy
import gi
import os

gi.require_version("Gst", "1.0")
gi.require_version("GstBase", "1.0")

from bpy.app.handlers import persistent
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gst
from gi.repository import GstBase
from gi.overrides import vfunc



Gst.init(None)


BLENDER_FILEPATH="/home/cfoch/Documents/git/cfoch-blender/simple/simple1.blend"
SCENE_NAME="Scene"
OUTPUT_FILEPATH="/home/cfoch/Pictures/blender/"


class GstBlenderSrc(GstBase.PushSrc):
    """
    Example:
        gst-launch-1.0 blendersrc location="foo.blend" \
            output-location="/tmp/" start-frame=120 end-frame=80 ! \
            decodebin ! videoconvert ! autovideosink
    """
    DEFAULT_LOCATION = ""
    DEFAULT_START_FRAME = 1
    DEFAULT_END_FRAME = 25
    DEFAULT_OUTPUT_LOCATION = "/tmp/"
    DEFAULT_PREFIX = ""
    DEFAULT_DELETE = False

    __gstmetadata__ = (
        "GstBlenderSrc",
        "Src/File",
        "Use the Blender renderer to pass output to GStreamer",
        "Fabian Orccon <cfoch.fabian@gmail.com>"
    )
    __gsttemplates__ = Gst.PadTemplate.new(
        "src",
        Gst.PadDirection.SRC,
        Gst.PadPresence.ALWAYS,
        Gst.Caps.new_any()
    )

    __gproperties__ = {
        "location": (
            str, "Location", "The path to the .blend file",
            DEFAULT_LOCATION,
            GObject.PARAM_READWRITE | GObject.PARAM_STATIC_STRINGS
        ),
        "start-frame": (
            int, "Start Frame", "The start frame number", 1, GLib.MAXINT,
            DEFAULT_START_FRAME, GObject.PARAM_READWRITE
        ),
        "end-frame": (
            int, "End Frame", "The end frame number", 1, GLib.MAXINT,
            DEFAULT_END_FRAME, GObject.PARAM_READWRITE
        ),
        "output-location": (
            str, "Output Location", "The folder of output files",
            DEFAULT_OUTPUT_LOCATION,
            GObject.PARAM_READWRITE | GObject.PARAM_STATIC_STRINGS
        ),
        "prefix": (
            str, "Prefix", "The filename prefix", DEFAULT_PREFIX,
            GObject.PARAM_READWRITE | GObject.PARAM_STATIC_STRINGS
        ),
        "delete": (
            bool, "Delete", "Whether delete the output files or not",
            DEFAULT_DELETE, GObject.PARAM_READWRITE
        )
    }

    def __init__(self):
        super(GstBase.PushSrc, self).__init__(self)

        # Properties
        self.location = self.DEFAULT_LOCATION
        self.start_frame = self.DEFAULT_START_FRAME
        self.end_frame = self.DEFAULT_END_FRAME
        self.output_location = self.DEFAULT_OUTPUT_LOCATION
        self.prefix = self.DEFAULT_PREFIX
        self.delete = self.DEFAULT_DELETE

        self.index = 1
        # self.is_rendering = False
        self.__is_valid = True

    def do_get_property(self, prop):
        if prop.name == "location":
            return self.location
        elif prop.name == "start-frame":
            return self.start_frame
        elif prop.name == "end-frame":
            return self.end_frame
        elif prop.name == "output-location":
            return self.output_location
        elif prop.name == "prefix":
            return self.prefix
        elif prop.name == "delete":
            return self.delete
        else:
            raise AttributeError('unknown property %s' % prop.name)

    def do_set_property(self, prop, value):
        if prop.name == "location":
            self.location = value
            if not os.path.isfile(self.location):
                self.__is_valid = False
                raise AttributeError('File %s does not exist' % self.location)
            bpy.ops.wm.open_mainfile(filepath=self.location)
            self.scene = bpy.data.scenes["Scene"]
            self.render = self.scene.render
            bpy.app.handlers.render_post.append(self.render_post)
        elif prop.name == "start-frame":
            self.start_frame = self.index = value
        elif prop.name == "end-frame":
            self.end_frame = value
        elif prop.name == "output-location":
            if self.__is_valid and not os.path.isdir(value):
                self.__is_valid = False
                raise AttributeError(
                    'Invalid location or file %s does not exist' % value)
            self.output_location = value
        elif prop.name == "prefix":
            self.prefix = value
        elif prop.name == "delete":
            self.detele = value
        else:
            raise AttributeError('unknown property %s' % prop.name)

    @persistent
    def render_post(self, scene):
        # self.is_rendering = False
        print(self.render.frame_path(self.scene.frame_current))

    def update_frame(self):
        basename = "%s%09d" % (self.prefix, self.index)
        extension = ".png"
        filename = basename + extension
        self.scene.frame_set(self.index)
        self.render.filepath = os.path.join(self.output_location, filename)

    def render_frame(self, animation=False):
        # self.is_rendering = True
        bpy.ops.render.render(animation=animation, scene=SCENE_NAME, write_still=True)

    def count_frames(self):
        return self.render.frame_end - self.render.frame_start + 1

    def read_frame(self):
        path = self.render.filepath
        if not os.path.isfile(path):
            return None

        with open(path, "rb") as f:
            data = f.read()
        return data

    @vfunc(GstBase.PushSrc)
    def do_create(self):
        logging.info("valid to create %r" % self.__is_valid)
        if not self.__is_valid:
            return Gst.FlowReturn.ERROR, None
        if self.index > self.end_frame or self.index < self.start_frame:
            return Gst.FlowReturn.EOS, None

        self.update_frame()
        self.render_frame()

        data = self.read_frame()

        if data is None:
            return Gst.FlowReturn.EOS, None

        buff = Gst.Buffer.new_wrapped(data)

        self.index += 1

        return Gst.FlowReturn.OK, buff


GObject.type_register(GstBlenderSrc)

__gstelementfactory__ = (
    "blendersrc",
    Gst.Rank.NONE,
    GstBlenderSrc
)
