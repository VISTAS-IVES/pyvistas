from OpenGL.GL import *

from vistas.core.graphics.shader import ShaderProgram
from vistas.core.paths import get_builtin_shader


class FeatureShaderProgram(ShaderProgram):
    """ The most basic shader class for coloring features. """

    def __init__(self):
        super().__init__()
        self.attach_shader(get_builtin_shader('feature_vert.glsl'), GL_VERTEX_SHADER)
        self.attach_shader(get_builtin_shader('feature_frag.glsl'), GL_FRAGMENT_SHADER)
        self.link_program()
        self.alpha = 1.0
        self.height_factor = 1.0
        self.height_offset = 5.0

    def pre_render(self, camera):
        super().pre_render(camera)
        self.uniform1f('alpha', self.alpha)
        self.uniform1f('heightFactor', self.height_factor)
        self.uniform1f('heightOffset', self.height_offset)
