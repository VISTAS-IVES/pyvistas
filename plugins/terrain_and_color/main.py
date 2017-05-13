from ctypes import c_uint, sizeof, c_float

import numpy
from OpenGL.GL import *

from vistas.core.color import RGBColor
from vistas.core.histogram import Histogram
from vistas.core.timeline import Timeline
from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.mesh import Mesh, MeshShaderProgram
from vistas.core.graphics.vector import Vector
from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.option import Option, OptionGroup
from vistas.core.plugins.visualization import VisualizationPlugin3D


class TerrainAndColorPlugin(VisualizationPlugin3D):

    id = 'terrain_and_color_plugin'
    name = 'Terrain & Color'
    description = 'Terrain visualization with color inputs.'
    author = 'Conservation Biology Institute'
    visualization_name = 'Terrain & Color'

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

        self._selected_point = None
        self._needs_terrain = self._needs_color = False
        self._needs_boundaries = False
        self._needs_flow = False

        self._is_filtered = False
        self._filter_min = self._filter_max = 0

        # Primary plugin options
        self._options = OptionGroup()

        color_group = OptionGroup("Colors")
        self._min_color = Option(self, Option.COLOR, "Min Color Value", RGBColor(0, 0, 255))
        self._max_color = Option(self, Option.COLOR, "Max Color Value", RGBColor(255, 0, 0))
        self._nodata_color = Option(self, Option.COLOR, "No Data Color", RGBColor(100, 100, 100))
        color_group.items = [self._min_color,self._max_color,self._nodata_color]

        value_group = OptionGroup("Values")
        self._min_value = Option(self, Option.FLOAT, "Minimum Value", 0.0)
        self._max_value = Option(self, Option.FLOAT, "Maximum Value", 0.0)
        value_group.items = [self._min_value, self._max_value]

        data_group = OptionGroup("Data")
        self._elevation_attribute = Option(self, Option.CHOICE, "Elevation Attribute", 0)
        self._attribute = Option(self, Option.CHOICE, "Data Attribute", 0)
        self._elevation_factor = Option(self, Option.SLIDER, "Elevation Factor", 1.0, min_value=0.0, max_value=5.0)
        data_group.items = [self._elevation_attribute, self._attribute, self._elevation_factor]

        graphics_group = OptionGroup("Graphics Options")
        self._hide_no_data = Option(self, Option.CHECKBOX, "Hide No Data Values", False)
        self._per_vertex_color = Option(self, Option.CHECKBOX, "Per Vertex Color", True)
        self._per_vertex_lighting = Option(self, Option.CHECKBOX, "Per Vertex Lighting", False)
        graphics_group.items = [self._hide_no_data, self._per_vertex_color, self._per_vertex_lighting]

        self._options.items = [color_group, value_group, data_group, graphics_group]

        # Secondary plugin options
        self.boundary_group = OptionGroup("Boundary")
        self._boundary_color = Option(self, Option.COLOR, "Boundary Color", RGBColor(0, 0, 0))
        self._boundary_width = Option(self, Option.FLOAT, "Boundary Width", 1.0)
        self.boundary_group.items = [self._boundary_color, self._boundary_width]

        self._flow_group = OptionGroup("Flow Options")
        # Todo - flow options

        self._animation_group = OptionGroup("Animation Options")
        # Todo - animation options

        self._accumulation_group = OptionGroup("Flow Accumulation Options")
        # Todo - accumulation options

        # Todo - listen to timeline changes?

    def get_options(self):
        return self._options

    def update_option(self, option=None):

        if option is self._attribute:
            self._needs_color = True

            # Todo - handle multiple attributes (i.e. NetCDF)
            stats = self.attribute_data.variable_stats("")
            self._min_value.value = stats.min_value
            self._max_value.value = stats.max_value

        # Todo - send PluginOptionEvent.OPTION_AVAILABLE
        elif option is self._elevation_attribute:
            self._needs_terrain = True
        elif option is self._boundary_width:
            self._needs_boundaries = True

        if self.flow_dir_data is not None:
            pass    # Todo - handle flow vector events

        self.refresh()

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
        return self._is_filtered

    @property
    def filter_histogram(self):
        if self.attribute_data is not None:
            return Histogram(self.get_data(1).get_grid("", Timeline.app().current_time))
        else:
            return Histogram()

    def set_filter(self, min_value, max_value):
        self._is_filtered = True
        self._filter_min, self._filter_max = min_value, max_value
        self.refresh()

    def clear_filter(self):
        self._is_filtered = False
        self.refresh()

    @property
    def filter_min(self):
        return self._filter_min

    @property
    def filter_max(self):
        return self._filter_max

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

        if self._needs_terrain:
            self._create_terrain_mesh()
            self._needs_terrain = False
            self._needs_color = False
        elif self._needs_color:
            self._update_terrain_color()
            self._needs_color = False

        if self._needs_boundaries:
            self._update_boundaries()
            self._needs_boundaries = False
        if self._needs_flow:
            self._update_flow()
            self._needs_flow = False

        shader = self.mesh_renderable.shader


        # Todo - UIPostRedisplay
        # Todo - Update legend window

    def _create_terrain_mesh(self):
        pass

    def _update_terrain_color(self):
        pass

    def _update_boundaries(self):
        pass    # Todo - implement boundaries

    def _update_flow(self):
        pass    # Todo - implement flow visualization


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
