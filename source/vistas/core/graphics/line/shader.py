from vistas.core.graphics.shader import ShaderProgram, GL_VERTEX_SHADER, GL_FRAGMENT_SHADER
from vistas.core.paths import get_builtin_shader

class SelectShaderProgram(ShaderProgram):

    def __init__(self):
        super().__init__()
        self.width = 800
        self.height = 600
        self.attach_shader(get_builtin_shader('select_vert.glsl'), GL_VERTEX_SHADER)
        self.attach_shader(get_builtin_shader('select_frag.glsl'), GL_FRAGMENT_SHADER)
        self.link_program()

    def pre_render(self, camera):
        self.uniform1f('width', self.width)
        self.uniform1f('height', self.height)
