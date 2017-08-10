import os

from OpenGL.GL import *

from vistas.core.graphics.mesh import Mesh, MeshShaderProgram
from vistas.core.graphics.renderable import Renderable
from vistas.core.paths import get_resources_directory


class MeshRenderable(Renderable):
    """ Base mesh renderable class, combining a Mesh and a MeshShaderProgram into an OpenGL-renderable object. """

    def __init__(self, mesh=None):
        super().__init__()

        self._mesh = None
        self.textures_map = {}
        self.mesh = Mesh() if mesh is None else mesh

    @property
    def mesh(self):
        return self._mesh

    @mesh.setter
    def mesh(self, mesh):
        self._mesh = mesh
        self.bounding_box = mesh.bounding_box
        self.textures_map = {}

    def render(self, camera):
        if self.mesh.has_index_array and self.mesh.has_vertex_array:
            for texture in self.textures_map.values():
                texture.pre_render(1, camera)

            self.mesh.shader.pre_render(camera)

            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.mesh.index_buffer)
            glDrawElements(self.mesh.mode, self.mesh.num_indices, GL_UNSIGNED_INT, None)

            self.mesh.shader.post_render(camera)

            for texture in self.textures_map.values():
                texture.post_render(1, camera)

            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

    @property
    def selection_shader(self):
        path = os.path.join(get_resources_directory(), 'shaders', 'mesh_render_for_selection_hit_vert.glsl')
        shader = MeshShaderProgram(self.mesh)
        shader.attach_shader(path, GL_VERTEX_SHADER)

        return shader

    def render_for_selection_hit(self, camera, r, g, b):
        if self.mesh is None:
            return

        shader = self.selection_shader
        shader.pre_render(camera)
        glUniform4f(shader.get_uniform_location('color'), r, g, b, 1.0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.mesh.index_buffer)

        glDrawElements(self.mesh.mode, self.mesh.num_indices, GL_UNSIGNED_INT, None)

        shader.post_render(camera)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

    def aqcuire_texture(self, texture):
        self.textures_map[texture.number] = texture

    def release_texture(self, number):
        return self.textures_map.pop(number)
