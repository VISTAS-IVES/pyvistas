from OpenGL.GL import *
from pyrr import Vector3

from vistas.core.color import RGBColor
from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.mesh import Mesh, MeshShaderProgram
from vistas.core.graphics.mesh_renderable import MeshRenderable
from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.visualization import VisualizationPlugin3D


class TestVisualizationPlugin(VisualizationPlugin3D):
    id = 'test_visualization_plugin'
    name = 'Test Visualization Plugin'
    description = 'Visualization plugin used for testing. Creates a cube object.'
    author = 'Conservation Biology Institute'
    visualization_name = 'Test Visualization'

    def __init__(self):
        super().__init__()

        self.data = None
        self.renderable = None
        self._scene = None

    @property
    def can_visualize(self):
        return True

    @property
    def data_roles(self):
        return [
            (DataPlugin.ARRAY, 'Color Data')
        ]

    def set_data(self, data: DataPlugin, role):
        if self.data != data:
            self.data = data

            if self.scene is not None and self.renderable is not None:
                self.scene.remove_object(self.renderable)
                self.renderable = None

    def get_data(self, role):
        return self.data

    @property
    def scene(self):
        return self._scene

    @scene.setter
    def scene(self, scene):
        if self.renderable is not None and self._scene is not None:
            self._scene.remove_object(self.renderable)

            if scene is not None:
                scene.add_object(self.renderable)
            else:
                self.renderable = None

        self._scene = scene

    def refresh(self):
        if self._scene is not None and self.renderable is None:
            mesh = Mesh(36, 8, True, False, mode=Mesh.TRIANGLES)
            mesh.bounding_box = BoundingBox(-1, -1, -1, 1, 1, 1)

            shader = TestShaderProgram(mesh)
            shader.color = RGBColor(*(x / 255 for x in self.data.get_data(None))) if self.data else RGBColor(1, 1, 1)
            shader.attach_shader(self.get_shader_path('vert.glsl'), GL_VERTEX_SHADER)
            shader.attach_shader(self.get_shader_path('frag.glsl'), GL_FRAGMENT_SHADER)

            mesh.shader = shader

            mesh_index_array = mesh.acquire_index_array()
            mesh_index_array[:] = [
                4, 0, 3,
                4, 3, 7,
                2, 6, 7,
                2, 7, 3,
                1, 5, 2,
                5, 6, 2,
                0, 4, 1,
                4, 5, 1,
                4, 7, 5,
                7, 6, 5,
                0, 1, 2,
                0, 2, 3
            ]
            mesh.release_index_array()

            mesh_vertex_array = mesh.acquire_vertex_array()
            mesh_vertex_array[:] = [
                1, -1, -1,
                1, -1, 1,
                -1, -1, 1,
                -1, -1, -1,
                1, 1, -1,
                1, 1, 1,
                -1, 1, 1,
                -1, 1, -1
            ]
            mesh.release_vertex_array()

            mesh_normal_array = mesh.acquire_normal_array()
            mesh_normal_array[:] = [
                0.408246, -0.816492, -0.408246,
                0.816492, -0.408246, 0.408246,
                -0.577349, -0.577349, 0.577349,
                -0.408246, -0.408246, -0.816492,
                0.666646, 0.333323, -0.666646,
                0.333323, 0.666646, 0.666646,
                -0.577349, 0.577349, 0.577349,
                -0.666646, 0.666646, -0.333323
            ]
            mesh.release_normal_array()

            self.renderable = MeshRenderable(mesh)
            self.renderable.position = Vector3([.75, .75, -2])
            self.renderable.scale = Vector3([.5, .5, .5])
            self.scene.add_object(self.renderable)


class TestShaderProgram(MeshShaderProgram):
    def __init__(self, mesh):
        super().__init__(mesh)

        self.color = RGBColor(1, 1, 1)

    def pre_render(self, camera):
        super().pre_render(camera)

        glUniform3fv(self.get_uniform_location('color'), 1, self.color.rgb.rgb_list)
