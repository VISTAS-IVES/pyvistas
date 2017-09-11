import numpy
from OpenGL.GL import *

from vistas.core.graphics.geometry import Geometry
from vistas.core.graphics.object import Object3D
from vistas.core.graphics.shader import ShaderProgram
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


class BoxDragGeometry(Geometry):

    INDICES = numpy.array([
        0, 1, 2, 3, 0
    ], dtype=numpy.uint8)

    def __init__(self):
        super().__init__(5, 4, mode=Geometry.LINE_STRIP)
        self.indices = self.INDICES




class DragSelectBox:
    def __init__(self):
        super().__init__()
        self._drawing = False
        self.geometry = None
        self.shader = None

    @property
    def drawing(self):
        return self._drawing

    @drawing.setter
    def drawing(self, drawing):
        self._drawing = drawing
        if not self._drawing:
            self.set_screen_coords(*[0, 0, 0, 0])

    def set_screen_coords(self, left=0, bottom=0, right=0, top=0):
        self.geometry.vertices = numpy.array([
            left, bottom, 0,
            right, bottom, 0,
            right, top, 0,
            left, top, 0,
        ], dtype=numpy.float32)

    def render(self, camera):
        if self.geometry is None:
            self.geometry = BoxDragGeometry()

        if self.shader is None:
            self.shader = SelectShaderProgram()

        glDisable(GL_DEPTH_TEST)
        glViewport(0, 0, self.shader.width, self.shader.height)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glUseProgram(self.shader.program)
        glBindVertexArray(self.geometry.vertex_array_object)
        self.shader.pre_render(camera)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.geometry.index_buffer)
        glDrawElements(self.geometry.mode, self.geometry.num_indices, GL_UNSIGNED_INT, None)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        self.shader.post_render(camera)
        glDisable(GL_BLEND)
