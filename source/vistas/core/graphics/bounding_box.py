import numpy
from OpenGL.GL import *

from vistas.core.graphics.objects import Object3D
from vistas.core.graphics.geometry import Geometry
from vistas.core.graphics.shader import ShaderProgram
from vistas.core.paths import get_builtin_shader


class BoundingBoxHelper(Object3D):
    """ Simple object to help visualize a Mesh's BoundingBox. """

    shader = None
    indices = numpy.array([
        0, 1,
        4, 5,
        2, 3,
        6, 7,
        0, 4,
        1, 5,
        2, 6,
        3, 7,
        0, 2,
        1, 3,
        4, 6,
        5, 7], dtype=GLint)

    def __init__(self, mesh):
        super().__init__()
        if BoundingBoxHelper.shader is None:
            BoundingBoxHelper.shader = ShaderProgram()
            BoundingBoxHelper.shader.attach_shader(get_builtin_shader('bbox_vert.glsl'), GL_VERTEX_SHADER)
            BoundingBoxHelper.shader.attach_shader(get_builtin_shader('bbox_frag.glsl'), GL_FRAGMENT_SHADER)
            BoundingBoxHelper.shader.link_program()

        self.mesh = mesh
        self.geometry = Geometry(24, 8, mode=GL_LINES)
        self.geometry.indices = self.indices
        self.update()

    def update(self):
        """ Update the vertex buffer based on the bounding box of the geometry we are attached to. """

        self.geometry.bounding_box = self.mesh.geometry.bounding_box
        bbox = self.geometry.bounding_box
        x_min = bbox.min_x
        x_max = bbox.max_x
        y_min = bbox.min_y
        y_max = bbox.max_y
        z_min = bbox.min_z
        z_max = bbox.max_z

        self.geometry.vertices = numpy.array([
            x_min, y_min, z_min,  # 0
            x_max, y_min, z_min,  # 1
            x_min, y_max, z_min,  # 2
            x_max, y_max, z_min,  # 3
            x_min, y_min, z_max,  # 4
            x_max, y_min, z_max,  # 5
            x_min, y_max, z_max,  # 6
            x_max, y_max, z_max   # 7
        ], dtype=GLfloat)

    def render(self, color, camera):
        self.shader.pre_render(camera)
        self.shader.uniform3fv("color", 1, color.rgb.rgb_list)
        glBindVertexArray(self.geometry.vertex_array_object)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.geometry.index_buffer)
        glDrawElements(GL_LINES, 24, GL_UNSIGNED_INT, None)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        self.shader.post_render(camera)
