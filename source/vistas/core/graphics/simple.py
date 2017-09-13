import numpy
from OpenGL.GL import *

from vistas.core.graphics.geometry import Geometry
from vistas.core.graphics.mesh import Mesh
from vistas.core.graphics.shader import ShaderProgram
from vistas.core.paths import get_builtin_shader


class BasicMaterial(ShaderProgram):

    def __init__(self):
        super().__init__()
        self.attach_shader(get_builtin_shader('simple_vert.glsl'), GL_VERTEX_SHADER)
        self.attach_shader(get_builtin_shader('simple_frag.glsl'), GL_FRAGMENT_SHADER)
        self.link_program()
        self.color = [0, 1, 0]

    def pre_render(self, camera):
        super().pre_render(camera)
        self.uniform3fv('color', 1, self.color)


class BasicGeometry(Geometry):

    VERTS = None
    INDICES = None

    def __init__(self):
        super().__init__(len(self.INDICES), len(self.VERTS) // 3, mode=Geometry.TRIANGLES)
        self.vertices = self.VERTS
        self.indices = self.INDICES
        self.compute_bounding_box()
        self.compute_normals()


class BoxGeometry(BasicGeometry):

    VERTS = numpy.array([
        1, -1, -1,
        1, -1, 1,
        -1, -1, 1,
        -1, -1, -1,
        1, 1, -1,
        1, 1, 1,
        -1, 1, 1,
        -1, 1, -1
    ], dtype=numpy.float32)

    INDICES = numpy.array([
        4, 0, 3,
        4, 3, 7,
        2, 6, 7,
        2, 7, 3,
        1, 5, 2,
        5, 6, 2,
        0, 4, 1,
        4, 5, 1,
        4, 7, 5,
        7, 6, 5,
        0, 1, 2,
        0, 2, 3
    ], dtype=numpy.uint8)


class Box(Mesh):
    def __init__(self):
        super().__init__(BoxGeometry(), BasicMaterial())
