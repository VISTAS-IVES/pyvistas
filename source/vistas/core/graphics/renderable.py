import copy
import os
from typing import List, Dict, Optional

import numpy
from OpenGL.GL import *
from pyrr import Vector3

from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.shader import ShaderProgram
from vistas.core.paths import get_resources_directory


class Renderable:
    """ Abstract renderable class. Subclasses implement a `render` method to perform OpenGL bindings. """

    class Face:
        """ Container for describing a face on a Renderable object """
        def __init__(self, a, b, c, normal=None, color=None):
            self.a = a
            self.b = b
            self.c = c
            self.normal = normal
            self.color = color

    class Intersection:
        """ Container for describing an intersection at a point on a Renderable object. """
        def __init__(self, distance, point, object):
            self.distance = distance
            self.point = point
            self.object = object
            self.uv = None
            self.face = None
            self.face_index = None

    bbox_shader_program = None
    bbox_indices = numpy.array([
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

    def __init__(self):
        # One-time initialization of bounding box shader program
        if Renderable.bbox_shader_program is None:
            Renderable.bbox_shader_program = ShaderProgram()
            Renderable.bbox_shader_program.attach_shader(
                os.path.join(get_resources_directory(), 'shaders', 'bbox_vert.glsl'), GL_VERTEX_SHADER
            )
            Renderable.bbox_shader_program.attach_shader(
                os.path.join(get_resources_directory(), 'shaders', 'bbox_frag.glsl'), GL_FRAGMENT_SHADER
            )
            Renderable.bbox_shader_program.link_program()

        self.scale = Vector3([1, 1, 1])
        self.position = Vector3()
        self.rotation = Vector3()
        self._bounding_box = None

        self.bbox_vao = None
        self.bbox_vertex_buffer = None
        self.bbox_index_buffer = None

        # Init the VAO
        self.bounding_box = BoundingBox(0, 0, 0, 0, 0, 0)

    def __del__(self):
        if self.bbox_vao is not None:
            glDeleteVertexArrays(1, self.bbox_vao)
            glDeleteBuffers(1, self.bbox_vertex_buffer)
            glDeleteBuffers(1, self.bbox_index_buffer)

    @property
    def bounding_box(self):
        return self._bounding_box

    @bounding_box.setter
    def bounding_box(self, bounding_box):
        self._bounding_box = bounding_box
        x_min = self.bounding_box.min_x
        x_max = self.bounding_box.max_x
        y_min = self.bounding_box.min_y
        y_max = self.bounding_box.max_y
        z_min = self.bounding_box.min_z
        z_max = self.bounding_box.max_z

        vertices = numpy.array([
            x_min, y_min, z_min,    # 0
            x_max, y_min, z_min,    # 1
            x_min, y_max, z_min,    # 2
            x_max, y_max, z_min,    # 3
            x_min, y_min, z_max,    # 4
            x_max, y_min, z_max,    # 5
            x_min, y_max, z_max,    # 6
            x_max, y_max, z_max     # 7
        ], dtype=GLfloat)

        # Init bbox VAO if need be
        if self.bbox_vao is None:
            self.bbox_vao = glGenVertexArrays(1)
            self.bbox_vertex_buffer = glGenBuffers(1)
            self.bbox_index_buffer = glGenBuffers(1)

            # One-time bind of index buffer
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.bbox_index_buffer)
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.bbox_indices.nbytes, self.bbox_indices, GL_STATIC_DRAW)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

        # Update VAO
        glBindVertexArray(self.bbox_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.bbox_vertex_buffer)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        position_loc = self.bbox_shader_program.get_attrib_location("position")
        glEnableVertexAttribArray(position_loc)
        glVertexAttribPointer(position_loc, 3, GL_FLOAT, GL_FALSE, 0, None)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def render(self, camera):
        pass

    def render_bounding_box(self, color, camera):
        self.bbox_shader_program.pre_render(camera)
        self.bbox_shader_program.uniform3fv("color", 1, color.rgb.rgb_list)
        glBindVertexArray(self.bbox_vao)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.bbox_index_buffer)

        glDrawElements(GL_LINES, 24, GL_UNSIGNED_INT, None)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        self.bbox_shader_program.post_render(camera)

    def render_for_selection_hit(self, camera, r, g, b):
        pass

    def get_selection_detail(self, point: Vector3) -> Optional[Dict]:
        pass

    def raycast(self, raycaster) -> List[Intersection]:
        """Returns a list of intersections from the raycaster to this renderable. """

        raise NotImplementedError

    @property
    def bounds(self):
        bounding_box = copy.copy(self.bounding_box)

        bounding_box.scale(self.scale)
        bounding_box.move(self.position)

        return bounding_box
