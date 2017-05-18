from ctypes import c_uint, sizeof, c_float

import numpy
import math
from OpenGL.GL import *

from vistas.core.color import RGBColor
from vistas.core.histogram import Histogram
from vistas.core.timeline import Timeline
from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.mesh import Mesh, MeshShaderProgram
from vistas.core.graphics.mesh_renderable import MeshRenderable
from vistas.core.graphics.vector import normalize_v3
from vistas.core.graphics.utils import map_buffer
from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.option import Option, OptionGroup
from vistas.core.plugins.visualization import VisualizationPlugin3D
from vistas.ui.utils import *


class TerrainAndColorPlugin(VisualizationPlugin3D):

    id = 'terrain_and_color_plugin'
    name = 'Terrain & Color'
    description = 'Terrain visualization with color inputs.'
    author = 'Conservation Biology Institute'
    visualization_name = 'Terrain & Color'

    def __init__(self):
        super().__init__()

        self.mesh_renderable = None
        #self.vector_renderable = None
        self._scene = None
        self._histogram = None

        # data inputs
        self.terrain_data = None
        self.attribute_data = None
        self.boundary_data = None
        self.flow_dir_data = None
        self.flow_acc_data = None

        self._selected_point = None
        self._needs_terrain = self._needs_color = False
        self._needs_boundaries = False
        self._needs_flow = False

        self._is_filtered = False
        self._filter_min = self._filter_max = 0

        # Primary plugin options
        self._options = OptionGroup()

        color_group = OptionGroup("Colors")
        self._min_color = Option(self, Option.COLOR, "Min Color Value", RGBColor(0, 0, 1))
        self._max_color = Option(self, Option.COLOR, "Max Color Value", RGBColor(1, 0, 0))
        self._nodata_color = Option(self, Option.COLOR, "No Data Color", RGBColor(0.5, 0.5, 0.5))
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
            post_newoptions_available(self)

        elif option is self._elevation_attribute:
            self._needs_terrain = True
        elif option is self._boundary_width:
            self._needs_boundaries = True

        if self.flow_dir_data is not None:
            pass    # Todo - handle flow vector events

        self.refresh()

    def timeline_changed(self):
        if self.terrain_data and self.terrain_data.time_info and self.terrain_data.time_info.is_temporal:
            self._needs_terrain = True
        self._needs_color = True
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

        if role == 0:
            self.terrain_data = data
            self._needs_terrain = True

        elif role == 1:
            self.attribute_data = data
            self._needs_color = True

            if data is not None:
                stats = data.variable_stats("")     # Todo - get attribute variable names
                self._min_value.value = stats.min_value
                self._max_value.value = stats.max_value
            else:
                self._min_value.value, self._max_value.value = 0, 0
            post_newoptions_available(self)

        elif role == 2:
            self.boundary_data = data
            self._needs_boundaries = True

        elif role == 3:
            self.flow_dir_data = data
            self._needs_flow = True

        elif role == 4:
            self.flow_acc_data = data
            # Todo - update flow min/max filters
            self._needs_flow = True

    def get_data(self, role):
        if role == 0:
            return self.terrain_data
        elif role == 1:
            return self.attribute_data
        elif role == 2:
            return self.boundary_data
        elif role == 3:
            return self.flow_dir_data
        elif role == 4:
            return self.flow_acc_data
        return None

    @property
    def is_filterable(self):
        return True

    @property
    def is_filtered(self):
        return self._is_filtered

    @property
    def filter_histogram(self):
        if self.attribute_data is not None:
            return Histogram(self.get_data(1).get_data("", Timeline.app().current))
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
        if self._scene is not None:

            if self.mesh_renderable is not None:
                self._scene.remove_object(self.mesh_renderable)
                # Todo: handle vector_renderable

        self._scene = scene

        if self.mesh_renderable is not None and self._scene is not None:
            self._scene.add_object(self.mesh_renderable)
            # Todo: handle vector_renderable

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

        if self.mesh_renderable is not None:
            shader = self.mesh_renderable.mesh.shader

            # Update shaders with Option values
            shader.hide_no_data = self._hide_no_data.value
            shader.per_vertex_color = self._per_vertex_color.value
            shader.per_vertex_lighting = self._per_vertex_lighting.value
            shader.min_value = self._min_value.value
            shader.max_value = self._max_value.value

            shader.min_color = self._min_color.value.hsv.hsva_list
            shader.max_color = self._max_color.value.hsv.hsva_list
            shader.nodata_color = self._nodata_color.value.hsv.hsva_list
            shader.boundary_color = self._boundary_color.value.hsv.hsva_list

            shader.height_factor = self._elevation_factor.value if self._elevation_factor.value > 0 else 0.01

            shader.is_filtered = self._is_filtered
            shader.filter_min = self._filter_min
            shader.filter_max = self._filter_max

        post_redisplay()
        post_new_legend()

    def _create_terrain_mesh(self):
        if self.terrain_data is not None:
            height_stats = self.terrain_data.variable_stats("")
            nodata_value = height_stats.nodata_value
            min_value = height_stats.min_value
            max_value = height_stats.max_value
            cellsize = self.terrain_data.resolution
            height_data = self.terrain_data.get_data("")        # Todo - get elevation attribute label (i.e. NetCDF support)

            if type(height_data) is numpy.ma.MaskedArray:
                height_data = height_data.data

            factor = 1.0
            height, width = height_data.shape

            num_indices = (height - 1) * width * 2 + ((height - 1) * 2 - 2)
            num_vertices = width * height

            max_height = math.sqrt(width * height * cellsize) / 2
            if max_value > max_height:
                factor = max_height / max_value

            # Compute heightfield
            heightfield = numpy.zeros((height, width, 3))
            indices = numpy.indices((height, width))
            heightfield[:, :, 0] = indices[0] * cellsize   # x
            heightfield[:, :, 2] = indices[1] * cellsize   # z
            heightfield[:, :, 1] = height_data
            heightfield[:, :, 1][heightfield[:, :, 1] != nodata_value] *= factor    # Apply factor where needed
            heightfield[:, :, 1][heightfield[:, :, 1] == nodata_value] = min_value  # Otherwise, set to min value

            mesh = Mesh(num_indices, num_vertices, True, True, False, mode=Mesh.TRIANGLE_STRIP)

            shader = TerrainAndColorShaderProgram(mesh)
            shader.attach_shader(self.get_shader_path('vert.glsl'), GL_VERTEX_SHADER)
            shader.attach_shader(self.get_shader_path('frag.glsl'), GL_FRAGMENT_SHADER)
            mesh.shader = shader

            # Compute indices for vertices
            index_array = []
            for i in range(height - 1):
                if i > 0:
                    index_array.append(i * width)
                for j in range(width):
                    index_array.append(i * width + j)
                    index_array.append((i + 1) * width + j)
                if i < height - 2:
                    index_array.append((i + 1) * width + (width - 1))

            assert(len(index_array) == num_indices)

            # Compute normals
            normals = self._compute_normals(heightfield, index_array)

            # Set mesh vertex array to heightfield
            vert_buf = mesh.acquire_vertex_array()
            vert_buf[:] = heightfield.ravel().tolist()
            mesh.release_vertex_array()

            # Set mesh normal array
            norm_buf = mesh.acquire_normal_array()
            norm_buf[:] = normals
            mesh.release_normal_array()

            # Set mesh index array
            index_buf = mesh.acquire_index_array()
            index_buf[:] = index_array
            mesh.release_index_array()

            mesh.bounding_box = BoundingBox(0, min_value * factor, 0,
                                            width * cellsize, max_value * factor, height * cellsize)

            self.mesh_renderable = MeshRenderable(mesh)
            self._scene.add_object(self.mesh_renderable)

            self._update_terrain_color()

    @staticmethod
    def _compute_normals(heightfield, indices):
        """ Calculate normals - 
        see https://sites.google.com/site/dlampetest/python/calculating-normals-of-a-triangle-mesh-using-numpy
        """

        verts = heightfield.reshape(-1, heightfield.shape[-1])
        faces = numpy.array([indices[i:i + 3] for i in range(len(indices) - 2)])
        norm = numpy.zeros(verts.shape, dtype=verts.dtype)
        tris = verts[faces]
        n = numpy.cross(tris[::, 1] - tris[::, 0], tris[::, 2] - tris[::, 0])
        normalize_v3(n)
        norm[faces[:, 0]] += n
        norm[faces[:, 1]] += n
        norm[faces[:, 2]] += n
        normalize_v3(norm)
        return norm.reshape(-1).tolist()

    def _update_terrain_color(self):

        if self.mesh_renderable is not None:
            shader = self.mesh_renderable.mesh.shader

            if self.terrain_data and self.attribute_data:
                shader.has_color = True

                # Retrieve color layer
                attribute = ''  # Todo - get attribute
                data = self.attribute_data.get_data(attribute, Timeline.app().current)

                if type(data) is numpy.ma.MaskedArray:
                    data = data.data

                height, width = data.shape
                shader.nodata_value = self.attribute_data.variable_stats(attribute).nodata_value
                size = sizeof(c_float) * width * height

                # Inform OpenGL of the new color buffer
                glBindBuffer(GL_ARRAY_BUFFER, shader.value_buffer)
                glBufferData(GL_ARRAY_BUFFER, size, None, GL_DYNAMIC_DRAW)
                buffer = map_buffer(GL_ARRAY_BUFFER, numpy.float32, GL_WRITE_ONLY, size)
                buffer[:] = data.ravel()
                glUnmapBuffer(GL_ARRAY_BUFFER)
                glBindBuffer(GL_ARRAY_BUFFER, 0)

                post_redisplay()
            else:
                shader.has_color = False

    def _update_boundaries(self):
        pass    # Todo - implement boundaries

    def _update_flow(self):
        pass    # Todo - implement flow visualization


class TerrainAndColorShaderProgram(MeshShaderProgram):
    def __init__(self, mesh):
        super().__init__(mesh)

        self.value_buffer = glGenBuffers(1)
        self.has_color = False
        self.has_boundaries = False
        self.hide_no_data = False
        self.per_vertex_color = True
        self.per_vertex_lighting = False

        self.is_filtered = False
        self.filter_min = self.filter_max = 0

        self.height_factor = 1.0
        self.nodata_value = 0.0
        self.min_value = 0.0
        self.max_value = 0.0
        self.min_color = [0, 0, 0, 1]
        self.max_color = [1, 0, 0, 1]
        self.nodata_color = [.5, .5, .5, 1]
        self.boundary_color = [0, 0, 0, 1]

    def __del__(self):
        glDeleteBuffers(1, self.value_buffer)

    def pre_render(self, camera):
        super().pre_render(camera)

        if self.has_color:
            value_loc = self.get_attrib_location("value")
            glBindBuffer(GL_ARRAY_BUFFER, self.value_buffer)
            glVertexAttribPointer(value_loc, 1, GL_FLOAT, GL_FALSE, sizeof(GLfloat), None)
            glEnableVertexAttribArray(value_loc)

        #if self.has_boundaries:
        #    pass    # Todo - implement Texture class or equivalent
        #    #boundary_coord_loc = self.get_attrib_location("boundaryTexCoord")

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
        glUniform4fv(self.get_uniform_location("minColor"), 1, self.min_color)
        glUniform4fv(self.get_uniform_location("maxColor"), 1, self.max_color)
        glUniform4fv(self.get_uniform_location("noDataColor"), 1, self.nodata_color)
        glUniform4fv(self.get_uniform_location("boundaryColor"), 1, self.boundary_color)

    def post_render(self, camera):
        #glBindTexture(GL_TEXTURE_2D, 0)
        glDisableVertexAttribArray(self.get_attrib_location("value"))
        #glDisableVertexAttribArray(self.get_attrib_location("boundaryTexCoord"))
        #glDisableVertexAttribArray(self.get_attrib_location("boundaryTexture"))
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        super().post_render(camera)
