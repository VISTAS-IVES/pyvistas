import numpy
import wx

from OpenGL.GL import *

from vistas.core.color import RGBColor
from vistas.core.graphics.shader import ShaderProgram
from vistas.core.paths import get_builtin_shader
from vistas.ui.utils import post_redisplay


class VectorFieldShaderProgram(ShaderProgram):
    """ A ShaderProgram for rendering effects onto a VectorGeometry. """

    def __init__(self):
        super().__init__()

        self.attach_shader(get_builtin_shader('vfield_vert.glsl'), GL_VERTEX_SHADER)
        self.attach_shader(get_builtin_shader('vfield_frag.glsl'), GL_FRAGMENT_SHADER)
        self.link_program()

        self.color = RGBColor(1, 1, 0)
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

    def OnNotify(self, event):
        self.animation_value = self.animation_value + 0.1 if self.animation_value <= 1.0 else -1
        post_redisplay()

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

    def pre_render(self, camera):
        super().pre_render(camera)
        self.uniform3fv("color", 1, self.color.rgb_list)
        self.uniform1f("scale", self.vector_scale)
        self.uniform1i("hideNoData", self.hide_no_data)
        self.uniform1f("noDataValue", self.nodata_value)
        self.uniform3fv("offsetMultipliers", 1, numpy.array(self.offset_multipliers))
        self.uniform1f("timer", self.animation_value)
        self.uniform1i("scaleMag", self.use_magnitude_scale)
        self.uniform1i("filterMag", self.use_mag_filter)
        self.uniform1f("vectorSpeed", self.vector_speed)
        self.uniform1f("magMin", self.mag_min)
        self.uniform1f("magMax", self.mag_max)

    def post_render(self, camera):

        super().post_render(camera)

