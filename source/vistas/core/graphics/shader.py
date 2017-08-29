import logging
import os

import numpy
import wx
from OpenGL.GL import *

from vistas.ui.utils import post_redisplay

logger = logging.getLogger(__name__)


# Todo - Add shader library for individual shader snippets
# This change would allow shaders to be much more modular in their construction
# We could also detect changes to the shader snippets, or have them 'compiled' and then edited.


class ShaderProgram(wx.PyEvtHandler):
    """ Base shader program implementation. Programs are recompiled when .glsl files are modified. """

    def __init__(self):
        self.program = -1

        self.shaders = {}
        self.file_infos = {}

        self.timer = wx.Timer()
        self.timer.Bind(wx.EVT_TIMER, self.on_notify)

    def attach_shader(self, path, type):
        if not os.path.exists(path):
            return False

        self.file_infos[type] = (path, os.path.getmtime(path))
        self.timer.Start(100, True)

        with open(path) as f:
            return self.attach_shader_source(f.read(), type)

    def attach_shader_source(self, source, type):
        shader = self.shaders.get(type, -1)

        if shader != -1:
            glDeleteShader(shader)
            self.shaders[type] = -1

        shader = glCreateShader(type)
        glShaderSource(shader, source)
        glCompileShader(shader)

        shader_ok = glGetShaderiv(shader, GL_COMPILE_STATUS)
        if not shader_ok:
            logger.error(glGetShaderInfoLog(shader))

            return False

        self.shaders[type] = shader

        if self.program != -1:
            glDeleteProgram(self.program)
            self.program = -1

        return True

    def link_program(self):
        if self.program != -1:
            return True

        self.program = glCreateProgram()

        for shader in (x for x in self.shaders.values() if x != -1):
            glAttachShader(self.program, shader)

        glLinkProgram(self.program)

        program_ok = glGetProgramiv(self.program, GL_LINK_STATUS)
        if not program_ok:
            logger.error(glGetProgramInfoLog(self.program))
            self.program = -1

            return False

        return True

    def pre_render(self, camera):
        self.link_program()
        glUseProgram(self.program)

        position = camera.get_position()

        self.uniform_matrix4fv('projectionMatrix', 1, False, camera.proj_matrix)
        self.uniform_matrix4fv('modelViewMatrix', 1, False, camera.matrix)
        self.uniform3f('cameraPosition', position.x, position.y, position.z)

    def post_render(self, camera):
        glUseProgram(0)

    def on_notify(self, event):

        # Suppress error dialog on access denied
        log_null = wx.LogNull()  # noqa: F841

        for shader_type, (path, last_mtime) in self.file_infos.items():
            mtime = os.path.getmtime(path)
            if last_mtime < mtime:
                logger.debug('Reloading {}...'.format(path))
                self.attach_shader(path, shader_type)
                post_redisplay()

        self.timer.Start(100, True)

    def get_uniform_location(self, name):
        return glGetUniformLocation(self.program, name)

    def get_attrib_location(self, name):
        return glGetAttribLocation(self.program, name)

    def uniform1i(self, name, value):
        glUniform1i(self.get_uniform_location(name), value)

    def uniform1f(self, name, value):
        glUniform1f(self.get_uniform_location(name), value)

    def uniform1ui(self, name, value):
        glUniform1ui(self.get_uniform_location(name), value)

    def uniform2i(self, name, value1, value2):
        glUniform2i(self.get_uniform_location(name), value1, value2)

    def uniform2f(self, name, value1, value2):
        glUniform2f(self.get_uniform_location(name), value1, value2)

    def uniform2ui(self, name, value1, value2):
        glUniform2ui(self.get_uniform_location(name), value1, value2)

    def uniform3i(self, name, value1, value2, value3):
        glUniform3i(self.get_uniform_location(name), value1, value2, value3)

    def uniform3f(self, name, value1, value2, value3):
        glUniform3f(self.get_uniform_location(name), value1, value2, value3)

    def uniform3ui(self, name, value1, value2, value3):
        glUniform3ui(self.get_uniform_location(name), value1, value2, value3)

    def uniform4i(self, name, value1, value2, value3, value4):
        glUniform4i(self.get_uniform_location(name), value1, value2, value3, value4)

    def uniform4f(self, name, value1, value2, value3, value4):
        glUniform4f(self.get_uniform_location(name), value1, value2, value3, value4)

    def uniform4ui(self, name, value1, value2, value3, value4):
        glUniform4ui(self.get_uniform_location(name), value1, value2, value3, value4)

    def uniform1iv(self, name, count, value):
        glUniform1iv(self.get_uniform_location(name), count, value)

    def uniform1fv(self, name, count, value):
        glUniform1fv(self.get_uniform_location(name), count, value)

    def uniform1uiv(self, name, count, value):
        glUniform1uiv(self.get_uniform_location(name), count, value)

    def uniform2iv(self, name, count, value):
        glUniform2iv(self.get_uniform_location(name), count, value)

    def uniform2fv(self, name, count, value):
        glUniform2fv(self.get_uniform_location(name), count, value)

    def uniform2uiv(self, name, count, value):
        glUniform2uiv(self.get_uniform_location(name), count, value)

    def uniform3iv(self, name, count, value):
        glUniform3iv(self.get_uniform_location(name), count, value)

    def uniform3fv(self, name, count, value):
        glUniform3fv(self.get_uniform_location(name), count, value)

    def uniform3uiv(self, name, count, value):
        glUniform3uiv(self.get_uniform_location(name), count, value)

    def uniform4iv(self, name, count, value):
        glUniform4iv(self.get_uniform_location(name), count, value)

    def uniform4fv(self, name, count, value):
        glUniform4fv(self.get_uniform_location(name), count, value)

    def uniform4uiv(self, name, count, value):
        glUniform4uiv(self.get_uniform_location(name), count, value)

    def uniform_matrix3fv(self, name, count, transpose: bool, value):
        glUniformMatrix3fv(self.get_uniform_location(name), count, transpose, numpy.array(value, dtype=numpy.float32))

    def uniform_matrix4fv(self, name, count, transpose: bool, value):
        glUniformMatrix4fv(self.get_uniform_location(name), count, transpose, numpy.array(value, dtype=numpy.float32))
