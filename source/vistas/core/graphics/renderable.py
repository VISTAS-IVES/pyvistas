import copy
import os

import numpy
from OpenGL.GL import *
from pyrr import Vector3

from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.shader import ShaderProgram
from vistas.core.paths import get_resources_directory


class Renderable:
    """ Abstract renderable class. Subclasses implement a `render` method to perform OpenGL bindings. """

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
        self.bounding_box = BoundingBox(0, 0, 0, 0, 0, 0)

    def render(self, camera):
        pass

    def render_bounding_box(self, color, camera):

        bbox_scale = 0.1
        x_margin = (self.bounding_box.max_x - self.bounding_box.min_x) * bbox_scale
        y_margin = (self.bounding_box.max_y - self.bounding_box.min_y) * bbox_scale
        z_margin = (self.bounding_box.max_z - self.bounding_box.min_z) * bbox_scale
        x_min = self.bounding_box.min_x - x_margin
        x_max = self.bounding_box.max_x + x_margin
        y_min = self.bounding_box.min_y - y_margin
        y_max = self.bounding_box.max_y + y_margin
        z_min = self.bounding_box.min_z - z_margin
        z_max = self.bounding_box.max_z + z_margin

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

        # Start render pipeline
        self.bbox_shader_program.pre_render(camera)
        self.bbox_shader_program.uniform3fv("color", 1, color.rgb.rgb_list)

        # Now setup buffers specific to this bbox
        vertex_buffer = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vertex_buffer)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        position_loc = self.bbox_shader_program.get_attrib_location("position")
        glEnableVertexAttribArray(position_loc)
        glVertexAttribPointer(position_loc, 3, GL_FLOAT, GL_FALSE, 0, None)

        index_buffer = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, index_buffer)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.bbox_indices.nbytes, self.bbox_indices, GL_STATIC_DRAW)

        # Render
        glDrawElements(GL_LINES, 24, GL_UNSIGNED_INT, None)

        # Unlink the shader program
        glDisableVertexAttribArray(position_loc)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.bbox_shader_program.post_render(camera)

        # Now teardown this program's buffers
        glDeleteBuffers(1, [vertex_buffer])
        glDeleteBuffers(1, [index_buffer])

    def render_for_selection_hit(self, camera, r, g, b):
        pass

    def get_selection_detail(self, width, height, x, y, camera):
        pass

    @property
    def bounds(self):
        bounding_box = copy.copy(self.bounding_box)

        bounding_box.scale(self.scale)
        bounding_box.move(self.position)

        return bounding_box
