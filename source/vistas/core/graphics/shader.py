import os

import logging
import wx
from OpenGL.GL import *

from vistas.core.graphics.camera import Camera, ViewMatrix

logger = logging.getLogger(__name__)


class ShaderProgram(wx.PyEvtHandler):
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

    def attach_shader_souce(self, source, type):
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

    def pre_render(self):
        self.link_program()
        glUseProgram(self.program)

        projection_matrix = glGetFloatv(GL_PROJECTION_MATRIX)
        modelview_matrix = glGetFloatv(GL_MODELVIEW_MATRIX)

        camera = Camera()
        camera.matrix = ViewMatrix.from_gl(GL_MODELVIEW_MATRIX)
        position = camera.get_position()

        self.uniform_matrix_4fv(self.get_uniform_location('projectionMatrix'), 1, False, projection_matrix)
        self.uniform_matrix_4fv(self.get_uniform_location('modelViewMatrix'), 1, False, modelview_matrix)
        self.uniform_3f(self.get_uniform_location('cameraPosition'), position.x, position.y, position.z)

    def post_render(self):
        glUseProgram(0)

    def on_notify(self, event):
        log_null = wx.LogNull()  # Suppress error dialog on access denied

        for shader_type, (path, last_mtime) in self.file_infos.items():
            mtime = os.path.getmtime(path)
            if last_mtime < mtime:
                logger.debug('Reloading {}...'.format(path))
                self.attach_shader(path, shader_type)
                # Todo: UIPostRedisplay()

        self.timer.Start(100, True)

    def get_uniform_location(self, name):
        return glGetUniformLocation(self.program, name)

    def get_attrib_location(self, name):
        return glGetAttribLocation(self.program, name)
