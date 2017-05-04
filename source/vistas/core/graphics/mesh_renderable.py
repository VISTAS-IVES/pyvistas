import os

from OpenGL.GL import *

from vistas.core.graphics.mesh import Mesh, MeshShaderProgram
from vistas.core.graphics.renderable import Renderable
from vistas.core.paths import get_resources_directory


class MeshRenderable(Renderable):
    def __init__(self, mesh=None):
        self._mesh = None
        self.textures_map = {}
        self.bounding_box = None
        self.mesh = Mesh() if mesh is None else mesh

    @property
    def mesh(self):
        return self._mesh

    @mesh.setter
    def mesh(self, mesh):
        self._mesh = mesh
        self.bounding_box = mesh.bounding_box
        self.textures_map = {}

    def render(self):
        if self.mesh.has_index_array and self.mesh.has_vertex_array:
            if self.mesh.shader is None:
                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.mesh.index_buffer)
                glBindBuffer(GL_ARRAY_BUFFER, self.mesh.vertex_buffer)

                glEnableClientState(GL_VERTEX_ARRAY)
                glVertexPointer(3, GL_FLOAT, 0, 0)

                if self.mesh.has_normal_array:
                    glBindBuffer(GL_ARRAY_BUFFER, self.mesh.normal_buffer)
                    glEnableClientState(GL_NORMAL_ARRAY)
                    glNormalPointer(GL_FLOAT, 0, 0)

                if self.mesh.has_color_array:
                    size = 4 if self.mesh.use_rgba else 3

                    glBindBuffer(GL_ARRAY_BUFFER, self.mesh.color_buffer)
                    glEnableClientState(GL_COLOR_ARRAY)
                    glColorPointer(size, GL_FLOAT, 0, 0)

            for texture in self.textures_map.values():
                texture.pre_render(1)

            self.pre_render()

            if self.mesh.shader is not None:
                self.mesh.shader.pre_render()
                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.mesh.index_buffer)

            glDrawElements(self.mesh.mode)

            if self.mesh.shader is not None:
                self.mesh.shader.post_render()

            for texture in self.textures_map.values():
                texture.post_render(1)

            if self.mesh.shader is None:
                glDisableClientState(GL_VERTEX_ARRAY)
                glDisableClientState(GL_NORMAL_ARRAY)
                glDisableClientState(GL_COLOR_ARRAY)
                glBindBuffer(GL_ARRAY_BUFFER, 0)

            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

    @property
    def selection_shader(self):
        path = os.path.join(get_resources_directory(), 'shaders', 'mesh_render_for_selection_hit_vert.glsl')
        shader = MeshShaderProgram(self.mesh)
        shader.attach_shader(path, GL_VERTEX_SHADER)

        return shader

    def render_for_selection_hit(self, color):
        if self.mesh is None:
            return

        shader = self.selection_shader

        self.pre_render()

        shader.pre_render()
        glUniform4f(shader.get_uniform_location('color'), *color.rgb.rgba_list)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.mesh.index_buffer)

        glDrawElements(self.mesh.mode, self.mesh.num_indices, GL_UNSIGNED_INT, 0)

        shader.post_render()
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

    def aqcuire_texture(self, texture):
        self.textures_map[texture.number] = texture

    def release_texture(self, number):
        return self.textures_map.pop(number)
