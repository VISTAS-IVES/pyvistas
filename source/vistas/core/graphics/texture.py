from typing import Union

import numpy
from OpenGL.GL import *
from PIL.Image import Image, FLIP_TOP_BOTTOM
from numpy.core.multiarray import ndarray


class Texture:
    """ Object representation of an OpenGL texture. """

    def __init__(self, data: Union[ndarray, Image]=None, width=None, height=None, src_format=GL_RGB, gl_format=GL_RGB):
        if isinstance(data, Image):
            data = data.transpose(FLIP_TOP_BOTTOM)
            width, height = data.size
            data = numpy.array(data.getdata())

        self.texture = glGenTextures(1)

        # Set texture params
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)

        if data is not None and width is not None and height is not None:
            glBindTexture(GL_TEXTURE_2D, self.texture)
            glTexImage2D(GL_TEXTURE_2D, 0, src_format, width, height, 0, gl_format, GL_UNSIGNED_BYTE, data)
            glBindTexture(GL_TEXTURE_2D, 0)

    def __del__(self):
        glDeleteTextures([self.texture])
