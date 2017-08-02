from ctypes import c_uint, sizeof, c_float

import numpy
from OpenGL.GL import *

from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.shader import ShaderProgram
from vistas.core.graphics.utils import map_buffer


class Mesh:
    """ Base geometry class for 3D objects. """

    POINTS = GL_POINTS
    LINE_STRIP = GL_LINE_STRIP
    LINES = GL_LINES
    TRIANGLE_STRIP = GL_TRIANGLE_STRIP
    TRIANGLE_FAN = GL_TRIANGLE_FAN
    TRIANGLES = GL_TRIANGLES
    QUAD_STRIP = GL_QUAD_STRIP
    QUADS = GL_QUADS
    POLYGON = GL_POLYGON

    def __init__(
            self, num_indices=0, num_vertices=0, has_normal_array=False, has_color_array=False,
            has_texture_coords=False, use_rgba=False, mode=TRIANGLE_STRIP
    ):
        self.bounding_box = BoundingBox(0, 0, 0, 0, 0, 0)
        self.shader = None

        self.num_indices = num_indices
        self.num_vertices = num_vertices

        self.mode = mode
        self.has_index_array = num_indices > 0
        self.has_vertex_array = num_vertices > 0
        self.has_normal_array = has_normal_array
        self.has_color_array = has_color_array
        self.has_texture_coords = has_texture_coords
        self.use_rgba = use_rgba

        self.vertex_array_object = glGenVertexArrays(1)

        glBindVertexArray(self.vertex_array_object)

        if self.has_index_array:
            self.index_buffer = glGenBuffers(1)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.index_buffer)
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, num_indices * sizeof(c_uint), None, GL_DYNAMIC_DRAW)

        if self.has_vertex_array:
            self.vertex_buffer = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.vertex_buffer)
            glBufferData(GL_ARRAY_BUFFER, num_vertices * 3 * sizeof(c_float), None, GL_DYNAMIC_DRAW)

        if self.has_normal_array:
            self.normal_buffer = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.normal_buffer)
            glBufferData(GL_ARRAY_BUFFER, num_vertices * 3 * sizeof(c_float), None, GL_DYNAMIC_DRAW)

        if self.has_color_array:
            size = 4 if self.use_rgba else 3

            self.color_buffer = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.color_buffer)
            glBufferData(GL_ARRAY_BUFFER, num_vertices * size * sizeof(c_float), None, GL_DYNAMIC_DRAW)

        if self.has_texture_coords:
            self.texcoords_buffer = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.texcoords_buffer)
            glBufferData(GL_ARRAY_BUFFER, num_vertices * 2 * sizeof(c_float), None, GL_STATIC_DRAW)

        # Inform OpenGL where each of the VBOs are located in a given shader program.
        if self.has_vertex_array:
            glBindBuffer(GL_ARRAY_BUFFER, self.vertex_buffer)  # location 0 = 'position'
            glEnableVertexAttribArray(0)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, sizeof(GLfloat) * 3, None)

        if self.has_normal_array:
            glBindBuffer(GL_ARRAY_BUFFER, self.normal_buffer)  # location 1 = 'normal'
            glEnableVertexAttribArray(1)
            glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, sizeof(GLfloat) * 3, None)

        if self.has_texture_coords:
            glBindBuffer(GL_ARRAY_BUFFER, self.texcoords_buffer)   # location 2 = 'uv', i.e. texcoords
            glEnableVertexAttribArray(2)
            glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, sizeof(GLfloat) * 2, None)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def __del__(self):
        if self.has_index_array:
            glDeleteBuffers(1, [self.index_buffer])

        if self.has_vertex_array:
            glDeleteBuffers(1, [self.vertex_buffer])

        if self.has_normal_array:
            glDeleteBuffers(1, [self.normal_buffer])

        if self.has_color_array:
            glDeleteBuffers(1, [self.color_buffer])

        if self.has_texture_coords:
            glDeleteBuffers(1, [self.texcoords_buffer])

        glDeleteVertexArrays(1, [self.vertex_array_object])

    def acquire_index_array(self):
        """ Note: Mesh.release_index_array() must be called once the buffer is no longer needed """

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.index_buffer)
        return map_buffer(GL_ELEMENT_ARRAY_BUFFER, numpy.uint32, GL_WRITE_ONLY, self.num_indices * sizeof(c_uint))

    def acquire_vertex_array(self):
        """ Note: Mesh.release_vertex_array() must be called once the buffer is no longer needed """

        glBindBuffer(GL_ARRAY_BUFFER, self.vertex_buffer)
        return map_buffer(GL_ARRAY_BUFFER, numpy.float32, GL_WRITE_ONLY, self.num_vertices * 3 * sizeof(c_float))

    def acquire_normal_array(self):
        """ Note: Mesh.release_normal_array() must be called once the buffer is no longer needed """

        glBindBuffer(GL_ARRAY_BUFFER, self.normal_buffer)
        return map_buffer(GL_ARRAY_BUFFER, numpy.float32, GL_WRITE_ONLY, self.num_vertices * 3 * sizeof(c_float))

    def acquire_color_array(self):
        """ Note: Mesh.release_color_array() must be called once the buffer is no longer needed """

        size = 4 if self.use_rgba else 3

        glBindBuffer(GL_ARRAY_BUFFER, self.color_buffer)
        return map_buffer(GL_ARRAY_BUFFER, numpy.float32, GL_WRITE_ONLY, self.num_vertices * size * sizeof(c_float))

    def acquire_texcoords_array(self):
        glBindBuffer(GL_ARRAY_BUFFER, self.texcoords_buffer)
        return map_buffer(GL_ARRAY_BUFFER, numpy.float32, GL_WRITE_ONLY, self.num_vertices * 2 * sizeof(c_float))

    def release_index_array(self):
        glUnmapBuffer(GL_ELEMENT_ARRAY_BUFFER)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

    def release_normal_array(self):
        glUnmapBuffer(GL_ARRAY_BUFFER)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def release_color_array(self):
        self.release_normal_array()

    def release_vertex_array(self):
        self.release_normal_array()

    def release_texcoords_array(self):
        self.release_normal_array()


class MeshShaderProgram(ShaderProgram):
    def __init__(self, mesh):
        super().__init__()

        self.mesh = mesh

    def pre_render(self, camera):
        super().pre_render(camera)
        glBindVertexArray(self.mesh.vertex_array_object)

    def post_render(self, camera):
        glBindVertexArray(0)
        super().post_render(camera)
