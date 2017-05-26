from OpenGL.GL import *


class Texture:
    def __init__(self, data=None, width=None, height=None, use_rgb=True):
        self.texture = glGenTextures(1)

        # Set texture params
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)

        if None not in [data, width, height]:
            self.teximage2d(data, width, height, use_rgb)

    def __del__(self):
        glDeleteTextures(1, self.texture)

    def teximage2d(self, data, width, height, use_rgb=True):

        glBindTexture(GL_TEXTURE_2D, self.texture)
        if use_rgb:
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB8, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, data)
        else:
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB8, width, height, 0, GL_RED, GL_UNSIGNED_BYTE, data)
        glBindTexture(GL_TEXTURE_2D, 0)

    # Todo - add support for float textures and other formats
