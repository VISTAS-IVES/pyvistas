from ctypes import c_uint, sizeof, c_float

import numpy
from OpenGL.GL import *

from vistas.core.color import RGBColor
from vistas.core.histogram import Histogram
from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.mesh import Mesh, MeshShaderProgram
from vistas.core.graphics.vector import Vector
from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.visualization import VisualizationPlugin3D


class TerrainAndColorPlugin(VisualizationPlugin3D):

    def __init__(self):
        super().__init__()

        self.mesh_renderable = None
        self.vector_renderable = None
        self._scene = None
        self._histogram = None

        # data inputs
        self.terrain_data = None
        self.attribute_data = None
        self.boundary_data = None
        self.flow_dir_data = None
        self.flow_acc_data = None

        # easy access to roles
        self._role_map = {
            0: self.terrain_data,
            1: self.attribute_data,
            2: self.boundary_data,
            3: self.flow_dir_data,
            4: self.flow_acc_data
        }

    @property
    def can_visualize(self):
        return self.terrain_data is not None

    @property
    def data_roles(self):
        return [
            (DataPlugin.RASTER, 'Terrain'),
            (DataPlugin.RASTER, 'Attribute'),
            (DataPlugin.FEATURE, 'Boundaries'),
            (DataPlugin.RASTER, 'Flow Direction'),
            (DataPlugin.RASTER, 'Flow Accumulation')
        ]

    def set_data(self, data: DataPlugin, role):

        if role not in self._role_map:
            return

        self._role_map[role] = data

        if self.scene is not None and self.mesh_renderable is not None:
            self.scene.remove_object(self.mesh_renderable)
            self.mesh_renderable = None

    def get_data(self, role):
        return self._role_map[role]

    @property
    def is_filterable(self):
        return True

    @property
    def is_filtered(self):
        return False    # Todo: Implement

    @property
    def filter_histogram(self):
        return Histogram(numpy.zeros(10))   # Todo: Implement

    @property
    def filter_min(self):
        return 0

    @property
    def filter_max(self):
        return 0

    @property
    def scene(self):
        return self._scene

    @scene.setter
    def scene(self, scene):
        if self.mesh_renderable is not None and self._scene is not None:
            self._scene.remove_object(self.mesh_renderable)     # Todo: handle vector_renderable
            if scene is not None:
                scene.add_object(self.mesh_renderable)
            else:
                self.mesh_renderable = None
        self._scene = scene

    def refresh(self):
        pass    # Todo: Implement


class TerrainAndColorShaderProgram(MeshShaderProgram):
    def __init__(self, mesh):
        super().__init__(mesh)

        self.value_buffer = -1
        self.has_color = False
        self.has_boundaries = False
        self.hide_no_data = False
        self.per_vertex_color = True
        self.per_vertex_lighting = False

        self.is_filtered = False
        self.filter_min = self.filter_max = 0

        self.height_factor = None
        self.nodata_value = None
        self.min_value = None
        self.max_value = None
        self.min_color = Vector(0, 0, 0, 0)
        self.max_color = Vector(0, 0, 0, 0)
        self.nodata_color = Vector(0, 0, 0, 0)
        self.boundary_color = Vector(0, 0, 0, 255)

    def pre_render(self, camera):
        super().pre_render(camera)

        if self.has_color:
            value_loc = self.get_attrib_location("value")
            glBindBuffer(GL_ARRAY_BUFFER, self.value_buffer)
            glVertexAttribPointer(value_loc, 1, GL_FLOAT, GL_FALSE, sizeof(c_float), 0)
            glEnableVertexAttribArray(value_loc)

        if self.has_boundaries:
            pass    # Todo - implement Texture class or equivalent
            #boundary_coord_loc = self.get_attrib_location("boundaryTexCoord")

        glUniform1i(self.get_uniform_location("hideNoData"), self.hide_no_data)
        glUniform1i(self.get_uniform_location("perVertexColor"), self.per_vertex_color)
        glUniform1i(self.get_uniform_location("perVertexLighting"), self.per_vertex_lighting)
        glUniform1i(self.get_uniform_location("hasColor"), self.has_color)
        glUniform1i(self.get_uniform_location("hasBoundaries"), self.has_boundaries)

        glUniform1i(self.get_uniform_location("isFiltered"), self.is_filtered)
        glUniform1f(self.get_uniform_location("filterMin"), self.filter_min)
        glUniform1f(self.get_uniform_location("filterMax"), self.filter_max)

        glUniform1f(self.get_uniform_location("heightFactor"), self.height_factor)
        glUniform1f(self.get_uniform_location("noDataValue"), self.nodata_value)
        glUniform1f(self.get_uniform_location("minValue"), self.min_value)
        glUniform1f(self.get_uniform_location("maxValue"), self.max_value)
        glUniform4fv(self.get_uniform_location("minColor"), self.min_color.v)
        glUniform4fv(self.get_uniform_location("maxColor"), self.max_color.v)
        glUniform4fv(self.get_uniform_location("noDataColor"), self.nodata_color.v)
        glUniform4fv(self.get_uniform_location("boundaryColor"), self.boundary_color.v)

    def post_render(self, camera):
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisableVertexAttribArray(self.get_attrib_location("value"))
        glDisableVertexAttribArray(self.get_attrib_location("boundaryTexCoord"))
        glDisableVertexAttribArray(self.get_attrib_location("boundaryTexture"))
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        super().post_render(camera)
