from ctypes import sizeof
import numpy

from OpenGL.GL import *
from vistas.core.graphics.utils import map_buffer


class Texture:

    def __init__(self, num_vertices=0):
        self.size = sizeof(GLfloat) * 2 * num_vertices
        self.texture = glGenTextures(1)
        self.buffer = glGenBuffers(1)

        # Allocate GPU memory for tex coords
        glBindBuffer(GL_ARRAY_BUFFER, self.buffer)
        glBufferData(GL_ARRAY_BUFFER, self.size, None, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def __del__(self):
        glDeleteTextures(1, self.texture)
        glDeleteBuffers(1, self.buffer)

    def acquire_texcoord_array(self):
        glBindBuffer(GL_ARRAY_BUFFER, self.buffer)
        return map_buffer(GL_ARRAY_BUFFER, numpy.float32, GL_WRITE_ONLY, self.size)

    def release_texcoord_array(self):
        glUnmapBuffer(GL_ARRAY_BUFFER)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def tex_image_2d(self, data, width, height, use_rgb=True):

        ch = 3 if use_rgb else 1

        glBindTexture(GL_TEXTURE_2D, self.texture)
        if use_rgb:
            glTexImage2D(GL_TEXTURE_2D, 0, ch, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, data)
        else:
            glTexImage2D(GL_TEXTURE_2D, 0, ch, width, height, 0, GL_RED, GL_UNSIGNED_BYTE, data)
        glBindTexture(GL_TEXTURE_2D, 0)
