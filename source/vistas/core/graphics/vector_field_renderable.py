from ctypes import sizeof, c_void_p
import numpy
import os

from OpenGL.GL import *
from OpenGL.GLU import *

import wx

from vistas.core.color import RGBColor
from vistas.core.graphics.shader import ShaderProgram
from vistas.core.graphics.vector import Vector
from vistas.core.graphics.renderable import Renderable
from vistas.core.paths import get_resources_directory
from vistas.ui.utils import post_redisplay


class VectorFieldRenderable(Renderable):

    VERTICES = numpy.array([
        # arrow shaft
        -.1, 0, 1,
        -.1, 0, -0.2,
        .1, 0, 1,
        .1, 0, -0.2,

        # arrow head
        -0.3, 0.0, 0.1,
        0.0, 0.3, 0.1,
        0.3, 0.0, 0.1,
        0.0, -0.3, 0.1,

        # tip
        0.0, 0.0, -0.5
    ], dtype=GLfloat)

    INDICES = numpy.array([
        # arrow shaft
        0, 1, 2,
        1, 2, 3,

        # rrow head base,
        4, 5, 6,
        4, 7, 6,

        # head
        4, 5, 8,
        5, 6, 8,
        6, 7, 8,
        7, 4, 8,
    ], dtype=GLushort)

    def __init__(self, data=None):
        super().__init__()
        self.shader = ShaderProgram()
        self.shader.attach_shader(os.path.join(get_resources_directory(), 'shaders', 'vfield_vert.glsl'),
                                  GL_VERTEX_SHADER)
        self.shader.attach_shader(os.path.join(get_resources_directory(), 'shaders', 'vfield_frag.glsl'),
                                  GL_FRAGMENT_SHADER)
        self.shader.link_program()

        self.color = RGBColor(1, 1, 0)
        self.offset = Vector(0, 0, 0)
        self.offset_multipliers = Vector(1, 1, 1)
        self.instances = 0
        self.visible = True
        self._animate = False
        self.animation_value = 0
        self._animation_speed = 100
        self.vector_scale = 1.0

        self.hide_no_data = True
        self.nodata_value = 1.0

        self.use_mag_filter = False
        self.mag_min = None
        self.mag_max = None

        self.use_magnitude_scale = False
        self.vector_speed = 1

        self.timer = wx.Timer()
        self.timer.Bind(wx.EVT_TIMER, self.OnNotify)
        self._vao = glGenVertexArrays(1)
        self._instance_buffer = glGenBuffers(1)

        self._index_buffer = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._index_buffer)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.INDICES.nbytes, self.INDICES, GL_STATIC_DRAW)

        self._vertex_buffer = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self._vertex_buffer)
        glBufferData(GL_ARRAY_BUFFER, self.VERTICES.nbytes, self.VERTICES, GL_STATIC_DRAW)

        glBindBuffer(GL_ARRAY_BUFFER, 0)

        if data is not None:
            self.set_vector_data(data)

    def __del__(self):
        self.timer.Stop()
        glDeleteBuffers(1, self._instance_buffer)
        glDeleteBuffers(1, self._vertex_buffer)
        glDeleteVertexArrays(1, self._vao)

    def OnNotify(self, event):
        self.animation_value = self.animation_value + 0.1 if self.animation_value <= 1.0 else -1
        post_redisplay()

    def set_vector_data(self, data):

        if len(data.shape) > 0:
            data = data.ravel()

        assert data.size % 7 == 0    # ensure array is 6 floats wide

        self.instances = int(data.size / 7)

        # Generate VAO and use layout locations 0-4 in shader program
        glBindVertexArray(self._vao)

        # Enable position array at location 0
        glBindBuffer(GL_ARRAY_BUFFER, self._vertex_buffer)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(GLfloat), c_void_p(0))

        # Generate instance buffer, bind data, and enable instanced locations
        self._instance_buffer = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self._instance_buffer)
        glBufferData(GL_ARRAY_BUFFER, sizeof(GLfloat) * 7 * self.instances, data, GL_STATIC_DRAW)

        # location 1 = offset
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 7 * sizeof(GLfloat), c_void_p(0))

        # location 2 = dir
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2, 1, GL_FLOAT, GL_FALSE, 7 * sizeof(GLfloat), c_void_p(3 * sizeof(GLfloat)))

        # location 3 = tilt
        glEnableVertexAttribArray(3)
        glVertexAttribPointer(3, 1, GL_FLOAT, GL_FALSE, 7 * sizeof(GLfloat), c_void_p(4 * sizeof(GLfloat)))

        # location 4 = magnitude
        glEnableVertexAttribArray(4)
        glVertexAttribPointer(4, 1, GL_FLOAT, GL_FALSE, 7 * sizeof(GLfloat), c_void_p(5 * sizeof(GLfloat)))

        # location 5 = data
        glEnableVertexAttribArray(5)
        glVertexAttribPointer(5, 1, GL_FLOAT, GL_FALSE, 7 * sizeof(GLfloat), c_void_p(6 * sizeof(GLfloat)))

        glBindBuffer(GL_ARRAY_BUFFER, 0)

        # Inform OpenGL buffers 1 - 4 are instanced arrays
        glVertexAttribDivisor(1, 1)
        glVertexAttribDivisor(2, 1)
        glVertexAttribDivisor(3, 1)
        glVertexAttribDivisor(4, 1)
        glVertexAttribDivisor(5, 1)
        glBindVertexArray(0)

    @property
    def animate(self):
        return self._animate

    @animate.setter
    def animate(self, value):
        self._animate = value
        if self._animate:
            self.timer.Start(self._animation_speed)
        else:
            self.timer.Stop()
            self.animation_value = 0

    @property
    def is_animating(self):
        return self.timer.IsRunning()

    @property
    def animation_speed(self):
        return self._animation_speed

    @animation_speed.setter
    def animation_speed(self, value):
        self._animation_speed = value
        if self.timer.IsRunning():
            self.timer.Stop()
            self.timer.Start(self._animation_speed)

    def render(self, camera):
        self.shader.pre_render(camera)

        self.shader.uniform3fv("color", 1, self.color.rgb_list)
        self.shader.uniform1f("scale", self.vector_scale)
        self.shader.uniform1i("hideNoData", self.hide_no_data)
        self.shader.uniform1f("noDataValue", self.nodata_value)
        self.shader.uniform3fv("offsetMultipliers", 1, self.offset_multipliers.v[:3])
        self.shader.uniform1f("timer", self.animation_value)
        self.shader.uniform1i("scaleMag", self.use_magnitude_scale)
        self.shader.uniform1i("filterMag", self.use_mag_filter)
        self.shader.uniform1f("vectorSpeed", self.vector_speed)
        self.shader.uniform1f("magMin", self.mag_min)
        self.shader.uniform1f("magMax", self.mag_max)
        glBindVertexArray(self._vao)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._index_buffer)
        instances = 0
        if self.visible:
            instances = self.instances
        glDrawElementsInstanced(GL_TRIANGLES, self.INDICES.nbytes, GL_UNSIGNED_SHORT, None, instances)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        self.shader.post_render(camera)
