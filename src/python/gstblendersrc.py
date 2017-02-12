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
    DEFAULT_DELETE = True
    DEFAULT_FPS_N = 1
    DEFAULT_FPS_D = 1

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
            DEFAULT_DELETE,
            GObject.PARAM_READWRITE | GObject.PARAM_STATIC_STRINGS
        ),
        # "framerate": (
        #     Gst.Fraction, "Framerate", "The framerate the scene will playback" \
        #     "at. Overrides the default scene framerate.", 1, 1, GLib.MAXINT,
        #     GLib.MAXINT, Gst.Fraction(DEFAULT_FPS_N, DEFAULT_FPS_D),
        #     GObject.PARAM_READWRITE | GObject.PARAM_STATIC_STRINGS
        # )
    }

    def __init__(self):
        super(GstBase.PushSrc, self).__init__(self)
        GstBase.BaseSrc.set_format(self, Gst.Format.TIME)

        # Properties
        self.location = self.DEFAULT_LOCATION
        self.start_frame = self.DEFAULT_START_FRAME
        self.end_frame = self.DEFAULT_END_FRAME
        self.output_location = self.DEFAULT_OUTPUT_LOCATION
        self.prefix = self.DEFAULT_PREFIX
        self.delete = self.DEFAULT_DELETE
        self.framerate = Gst.Fraction(self.DEFAULT_FPS_N, self.DEFAULT_FPS_D)

        self.index = 1
        # self.is_rendering = False
        self.__is_valid = True
        self.__duration = None

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
        # elif prop.name == "framerate":
        #     return self.framerate
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
        # elif prop.name == "framerate":
        #     self.framerate= value
        else:
            raise AttributeError('unknown property %s' % prop.name)

    @persistent
    def render_post(self, scene):
        # self.is_rendering = False
        print(self.render.frame_path(self.scene.frame_current))

    def build_current_filename(self):
        basename = "%s%09d" % (self.prefix, self.index)
        extension = ".png"
        filename = basename + extension
        return filename

    def build_current_output_path(self):
        filename = self.build_current_filename()
        return os.path.join(self.output_location, filename)

    def update_frame(self):
        self.scene.frame_set(self.index)
        self.render.filepath = self.build_current_output_path()

    def render_frame(self, animation=False):
        bpy.ops.render.render(animation=animation, scene="Scene",
            write_still=True)

    def count_frames(self):
        return self.end_frame - self.start_frame + 1

    def calculate_duration(self):
        return Gst.util_uint64_scale(Gst.SECOND * self.count_frames(),
            self.framerate.denom, self.framerate.num)

    def read_frame(self):
        path = self.render.filepath
        if not os.path.isfile(path):
            return None
        with open(path, "rb") as f:
            data = f.read()
        if self.delete:
            os.remove(path)
        return data

    @vfunc(GstBase.BaseSrc)
    def do_is_seekable(self):
        if self.__duration is not None:
            return True
        return False

    @vfunc(GstBase.BaseSrc)
    def do_do_seek(self, segment):
        reverse = segment.rate < 0
        if reverse:
            return False

        segment.time = segment.start
        self.index = self.start_frame + segment.position *\
            self.framerate.num / (self.framerate.denom * Gst.SECOND)
        return True

    @vfunc(GstBase.BaseSrc)
    def do_get_caps(self, filter):
        return Gst.Caps.new_any()

    @vfunc(GstBase.PushSrc)
    def do_query(self, query):
        query.mini_object.refcount -= 1
        if query.type == Gst.QueryType.DURATION:
            fmt = query.parse_duration()[0]
            if fmt == Gst.Format.TIME:
                if self.__duration is not None:
                    query.set_duration(fmt, self.__duration)
                    query.mini_object.refcount += 1
                return True
        ret = GstBase.BaseSrc.do_query(self, query)
        query.mini_object.refcount += 1
        return ret

    @vfunc(GstBase.PushSrc)
    def do_create(self):
        if not self.__is_valid:
            return Gst.FlowReturn.ERROR, None

        if self.index > self.end_frame or self.index < self.start_frame:
            return Gst.FlowReturn.EOS, None

        self.__duration = self.calculate_duration()
        self.update_frame()
        self.render_frame()

        data = self.read_frame()

        if data is None:
            return Gst.FlowReturn.EOS, None

        buff = Gst.Buffer.new_wrapped(data)

        # TODO
        # Duration shouldn't be double. Check that.
        duration = Gst.SECOND * self.framerate.denom / self.framerate.num

        buff.pts = (self.index - self.start_frame) * duration
        buff.duration = duration
        buff.offset = self.index - self.start_frame
        buff.offset_end = self.index - self.start_frame + 1

        self.index += 1

        return Gst.FlowReturn.OK, buff


GObject.type_register(GstBlenderSrc)

__gstelementfactory__ = (
    "blendersrc",
    Gst.Rank.NONE,
    GstBlenderSrc
)
