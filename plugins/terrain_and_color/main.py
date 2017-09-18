import math
from collections import OrderedDict

import numpy
import shapely.geometry
from OpenGL.GL import GL_RGB8
from pyrr import Vector3
from rasterio import features
from rasterio import transform

from vistas.core.color import RGBColor
from vistas.core.graphics.mesh import Mesh
from vistas.core.graphics.terrain import TerrainColorGeometry, TerrainColorShaderProgram
from vistas.core.graphics.texture import Texture
from vistas.core.graphics.vector import VectorGeometry, VectorShaderProgram
from vistas.core.histogram import Histogram
from vistas.core.legend import StretchedLegend
from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.option import Option, OptionGroup
from vistas.core.plugins.visualization import VisualizationPlugin3D
from vistas.core.timeline import Timeline
from vistas.ui.utils import *


class TerrainAndColorPlugin(VisualizationPlugin3D):

    id = 'terrain_and_color_plugin'
    name = 'Terrain & Color'
    description = 'Terrain visualization with color inputs.'
    author = 'Conservation Biology Institute'
    version = '1.0'
    visualization_name = 'Terrain & Color'

    def __init__(self):
        super().__init__()

        self.terrain_mesh = None
        self.vector_mesh = None

        self._scene = None
        self._histogram = None

        # data inputs
        self.terrain_data = None
        self.attribute_data = None
        self.boundary_data = None
        self.flow_dir_data = None
        self.flow_acc_data = None

        self.selected_point = (-1, -1)
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
        color_group.items = [self._min_color, self._max_color,self._nodata_color]

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
        self._boundary_group = OptionGroup("Boundary")
        self._boundary_color = Option(self, Option.COLOR, "Boundary Color", RGBColor(0, 0, 0))
        self._boundary_width = Option(self, Option.FLOAT, "Boundary Width", 1.0)
        self._boundary_group.items = [self._boundary_color, self._boundary_width]

        self._flow_group = OptionGroup("Flow Options")
        self._show_flow = Option(self, Option.CHECKBOX, "Show Flow Direction", True)
        self._hide_no_data_vectors = Option(self, Option.CHECKBOX, "Hide No Data Vectors", True)
        self._flow_stride = Option(self, Option.INT, "Stride", 1, 1, 10)
        self._flow_color = Option(self, Option.COLOR, "Vector Color", RGBColor(1, 1, 0))
        self._flow_scale = Option(self, Option.SLIDER, "Vector Scale", 1.0, 0.01, 20.0)
        self._flow_group.items = [self._show_flow, self._hide_no_data_vectors, self._flow_stride, self._flow_color,
                                  self._flow_scale]

        self._animation_group = OptionGroup("Animation Options")
        self._animate_flow = Option(self, Option.CHECKBOX, "Enable Flow Animation", False)
        self._animation_speed = Option(self, Option.INT, "Animation Speed (ms)", 100)
        self._vector_speed = Option(self, Option.SLIDER, "Animation Speed Factor", 1.0, 0.01, 5.0)
        self._animation_group.items = [self._animate_flow, self._animation_speed, self._vector_speed]

        self._accumulation_group = OptionGroup("Flow Accumulation Options")
        self._acc_filter = Option(self, Option.CHECKBOX, "Enable Accumulation Filter", False)
        self._acc_min = Option(self, Option.INT, "Accumulation Min", 0)
        self._acc_max = Option(self, Option.INT, "Accumulation Max", 0)
        self._acc_scale = Option(self, Option.CHECKBOX, "Scale Flow by Acc. Value", False)
        self._accumulation_group.items = [self._acc_filter, self._acc_min, self._acc_max, self._acc_scale]

    def get_options(self):
        options = OptionGroup()
        options.items = self._options.items.copy()
        if self.boundary_data is not None:
            options.items.append(self._boundary_group)
        if self.flow_dir_data is not None:
            options.items.append(self._flow_group)
            options.items.append(self._animation_group)
            if self.flow_acc_data is not None:
                options.items.append(self._accumulation_group)
        return options

    def update_option(self, option: Option=None):

        if option is None or option.plugin is not self:
            return

        name = option.name

        if name in [self._min_color.name, self._max_color.name, self._min_value.name, self._max_value.name]:
            post_new_legend()

        elif name == self._attribute.name:
            self._needs_color = True
            stats = self.attribute_data.variable_stats(self._attribute.selected)
            self._min_value.value = stats.min_value
            self._max_value.value = stats.max_value
            post_newoptions_available(self)
            post_new_legend()

        elif name == self._elevation_attribute.name:
            self._needs_terrain = True

        elif name is self._boundary_width.name:
            self._needs_boundaries = True

        if self.flow_dir_data is not None:

            vector_shader = self.vector_mesh.shader

            if name == self._animate_flow.name:
                vector_shader.animate = self._animate_flow.value

            elif name == self._animation_speed.name:
                vector_shader.animation_speed = self._animation_speed.value

            elif name == self._elevation_factor.name:
                self.vector_mesh.geometry.vertex_scalars = Vector3(
                    [1, 1, self._elevation_factor.value], dtype=numpy.float32
                )

            elif name == self._flow_color.name:
                vector_shader.color = self._flow_color.value

            elif name == self._flow_scale.name:
                vector_shader.vector_scale = self._flow_scale.value

            elif name == self._show_flow.name:
                self.vector_mesh.visible = self._show_flow.value

            elif name == self._hide_no_data_vectors.name:
                vector_shader.hide_no_data = self._hide_no_data_vectors.value

            elif name == self._acc_filter.name:
                vector_shader.use_mag_filter = self._acc_filter.value and self.flow_acc_data is not None

            elif name == self._vector_speed.name:
                vector_shader.vector_speed = self._vector_speed.value

            elif name in [self._acc_min.name, self._acc_max.name]:
                vector_shader.mag_min = self._acc_min.value
                vector_shader.mag_max = self._acc_max.value

            elif name == self._acc_scale.name:
                vector_shader.use_magnitude_scale = self._acc_scale.value and self.flow_acc_data is not None

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

            if data is not None:
                self._elevation_attribute.labels = data.variables
            else:
                self._elevation_attribute.labels = []
            post_newoptions_available(self)

        elif role == 1:
            self.attribute_data = data
            self._needs_color = True

            if data is not None:
                stats = data.variable_stats(data.variables[0])
                self._min_value.value = round(stats.min_value, 6)   # User can specify higher sig figs
                self._max_value.value = round(stats.max_value, 6)
                self._attribute.value = 0
                self._attribute.labels = data.variables
            else:
                self._min_value.value, self._max_value.value = 0, 0
                self._attribute.labels = []
            post_newoptions_available(self)
            post_new_legend()

        elif role == 2:
            self.boundary_data = data
            self._needs_boundaries = True

        elif role == 3:
            self.flow_dir_data = data
            self._needs_flow = True
            post_newoptions_available(self)

        elif role == 4:
            self.flow_acc_data = data
            self._needs_flow = True

            if data is not None:
                stats = data.variable_stats(data.variables[0])
                self._acc_min.value, self._acc_max.value = stats.min_value, stats.max_value
            else:
                self._acc_min.value, self._acc_max.value = 0, 0
            post_newoptions_available(self)

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
            variable = self._attribute.selected
            nodata_value = self.attribute_data.variable_stats(variable).nodata_value
            return Histogram(self.attribute_data.get_data(variable, Timeline.app().current), nodata_value)
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

            if self.terrain_mesh is not None:
                self._scene.remove_object(self.terrain_mesh)

            if self.vector_mesh is not None:
                self._scene.remove_object(self.vector_mesh)

        self._scene = scene

        if self.terrain_mesh is not None and self._scene is not None:
            self._scene.add_object(self.terrain_mesh)

        if self.vector_mesh is not None and self._scene is not None:
            self._scene.add_object(self.vector_mesh)

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

        if self.terrain_mesh is not None:
            shader = self.terrain_mesh.shader

            # Update shaders with Option values
            shader.hide_no_data = self._hide_no_data.value
            shader.per_vertex_color = self._per_vertex_color.value
            shader.per_vertex_lighting = self._per_vertex_lighting.value
            shader.min_value = self._min_value.value
            shader.max_value = self._max_value.value

            # If attribute data does not specify a nodata_value, set something that won't affect rendering
            if self.attribute_data:
                stats = self.attribute_data.variable_stats(self._attribute.selected)
                if stats.nodata_value is None:
                    shader.nodata_value = stats.min_value - 1

            shader.min_color = self._min_color.value.hsv.hsva_list
            shader.max_color = self._max_color.value.hsv.hsva_list
            shader.nodata_color = self._nodata_color.value.hsv.hsva_list
            shader.boundary_color = self._boundary_color.value.hsv.hsva_list

            shader.height_factor = self._elevation_factor.value if self._elevation_factor.value > 0 else 0.01

            shader.is_filtered = self._is_filtered
            shader.filter_min = self._filter_min
            shader.filter_max = self._filter_max

        post_redisplay()

    def _create_terrain_mesh(self):
        if self.terrain_data is not None:

            if self.terrain_mesh is not None:    # height grid was set before, needs to be removed
                self._scene.remove_object(self.terrain_mesh)
                self.terrain_mesh.geometry.dispose()
                self.terrain_mesh = None

            elevation_attribute = self._elevation_attribute.selected
            height_stats = self.terrain_data.variable_stats(elevation_attribute)
            nodata_value = height_stats.nodata_value
            min_value = height_stats.min_value
            max_value = height_stats.max_value
            cellsize = self.terrain_data.resolution
            height_data = self.terrain_data.get_data(elevation_attribute)
            if isinstance(height_data, numpy.ma.MaskedArray):
                height_data = height_data.data

            factor = 1.0
            height, width = height_data.shape

            max_height = math.sqrt(width * height * cellsize) / 2
            if max_value > max_height:
                factor = max_height / max_value

            height_data[height_data != nodata_value] *= factor      # Apply factor where needed
            height_data[height_data == nodata_value] = min_value    # Otherwise, set to min value

            geometry = TerrainColorGeometry(width, height, cellsize, height_data)
            shader = TerrainColorShaderProgram()
            mesh = Mesh(geometry, shader, plugin=self)

            self.terrain_mesh = mesh
            self._scene.add_object(self.terrain_mesh)
            self._update_terrain_color()
        else:
            if self.terrain_mesh is not None:
                self._scene.remove_object(self.terrain_mesh)
                self.terrain_mesh.geometry.dispose()
                self.terrain_mesh = None

    def _update_terrain_color(self):
        if self.terrain_mesh is not None:
            shader = self.terrain_mesh.shader
            if self.terrain_data and self.attribute_data:
                shader.has_color = True

                # Retrieve color layer
                attribute = self._attribute.selected
                data = self.attribute_data.get_data(attribute, Timeline.app().current)

                if type(data) is numpy.ma.MaskedArray:
                    data = data.data

                color_stats = self.attribute_data.variable_stats(attribute)
                if color_stats.nodata_value:
                    shader.nodata_value = color_stats.nodata_value

                self.terrain_mesh.geometry.values = data
                post_redisplay()
            else:
                shader.has_color = False

    def _update_boundaries(self):
        if self.terrain_mesh is None:
            return

        shader = self.terrain_mesh.shader
        if self.terrain_data is not None:
            shader.has_boundaries = True

            # Create boundary image
            texture_w, texture_h = 512, 512
            image_data = numpy.ones((texture_h, texture_w, 3), dtype=numpy.uint8) * 255

            terrain_extent = self.terrain_data.extent
            if self.boundary_data is not None:
                # Burn geometry to texture
                shapes = self.boundary_data.get_features()
                image_data[:, :, 0] = numpy.fliplr(features.rasterize(
                    [shapely.geometry.shape(f['geometry']).exterior for f in shapes
                        if f['geometry']['type'] == 'Polygon'],
                    out_shape=(texture_h, texture_w), fill=255, default_value=0,
                    transform=transform.from_bounds(*terrain_extent.as_list(), texture_w, texture_h)
                )).T

            if self.selected_point != (-1, -1):
                p = self.selected_point
                cell_size = self.terrain_data.resolution
                grid_width, grid_height = self.terrain_data.shape
                xscale = texture_w / terrain_extent.width
                yscale = texture_h / terrain_extent.height
                box_w, box_h = cell_size * xscale, cell_size * yscale
                center = (int(p[0] / grid_width * texture_w), int(512 - p[1] / grid_height * texture_h))

                # Draw black rectangle directly into data
                min_x = min(max(center[0] - box_w / 2, 0), 510)
                max_x = min(max(center[0] + box_w / 2, min_x + 1), 511)
                min_y = min(max(center[1] - box_h / 2, 0), 510)
                max_y = min(max(center[1] + box_h / 2, min_y + 1), 511)

                image_data[round(min_y): round(max_y), round(min_x): round(max_x), 0] = 0

            shader.boundary_texture = Texture(
                data=image_data.ravel(), width=texture_w, height=texture_h, src_format=GL_RGB8
            )
        else:
            shader.has_boundaries = False
            shader.boundary_texture = Texture()

    def _update_flow(self):
        if self.terrain_data is not None and self.flow_dir_data is not None:

            height_label = self._elevation_attribute.selected
            flow_dir_label = self.flow_dir_data.variables[0]
            flow_acc_label = self.flow_acc_data.variables[0] if self.flow_acc_data is not None else ""
            attribute_label = self._attribute.selected if self.attribute_data is not None else ""

            height_data = self.terrain_data.get_data(height_label, Timeline.app().current)
            flow_dir = self.flow_dir_data.get_data(flow_dir_label, Timeline.app().current)

            height, width = flow_dir.shape

            if not flow_dir.shape == height_data.shape:
                post_message("Terrain and flow grids don't match. Did you load the correct flow grid for this terrain?",
                             MessageEvent.ERROR)
                return

            # Clobber all the data into one big array
            vector_data = numpy.zeros((height, width, VectorGeometry.BUFFER_WIDTH), dtype=numpy.float32)
            vector_data[:, :, 0:3] = self.terrain_mesh.geometry.vertices.reshape((height, width, 3))
            vector_data[:, :, 3] = flow_dir * -45.0 + 45.0       # VELMA flow direction, converted to polar degrees
            vector_data[:, :, 4] = 90 - numpy.arcsin(numpy.abs(
                self.terrain_mesh.geometry.normals.reshape((height, width, 3))[:, :, 2]
            )) * 180 / numpy.pi
            vector_data[:, :, 5] = numpy.ones((height, width), dtype=numpy.float32) if self.flow_acc_data is None else \
                self.flow_acc_data.get_data(flow_acc_label, Timeline.app().current)
            vector_data[:, :, 6] = numpy.zeros((height, width), dtype=numpy.float32) if self.attribute_data is None \
                else self.attribute_data.get_data(attribute_label, Timeline.app().current)

            # Inform vector_renderable of attribute grid (if set) so shader knows whether to hide nodata values
            if self.attribute_data is not None:
                nodata_value = self.attribute_data.variable_stats(attribute_label).nodata_value
            else:
                nodata_value = 1.0

            if self.vector_mesh is None:
                self.vector_mesh = Mesh(
                    VectorGeometry(max_instances=width * height, data=vector_data),
                    VectorShaderProgram()
                )
                self.scene.add_object(self.vector_mesh)
            else:
                self.vector_mesh.geometry.vector_data = vector_data

            self.vector_mesh.shader.nodata_value = nodata_value
            self.vector_mesh.shader.use_mag_filter = self._acc_filter.value and self.flow_acc_data is not None
            self.vector_mesh.shader.mag_min = self._acc_min.value
            self.vector_mesh.shader.mag_max = self._acc_max.value
            self.vector_mesh.shader.use_magnitude_scale = self._acc_scale.value and self.flow_acc_data is not None
            self.vector_mesh.visible = self._show_flow.value

        elif self.vector_mesh is not None:
            self.scene.remove_object(self.vector_mesh)
            self.vector_mesh = None

    def has_legend(self):
        return self.attribute_data is not None

    def get_legend(self, width, height):
        legend = StretchedLegend(self._min_value.value, self._max_value.value, self._min_color.value,
                                 self._max_color.value)
        return legend.render(width, height)

    def get_identify_detail(self, point):
        if self.terrain_data is not None:
            res = self.terrain_data.resolution
            cell_x = int(round((point.x / res)))
            cell_y = int(round((point.y / res)))

            terrain_attr = self._elevation_attribute.selected
            terrain_ref = self.terrain_data.get_data(terrain_attr)

            if self.attribute_data is not None:
                attribute_ref = self.attribute_data.get_data(
                    self._attribute.selected, Timeline.app().current
                )
                attr_width, attr_height = attribute_ref.shape
                if 0 <= cell_x < attr_width and 0 <= cell_y < attr_height:

                    result = OrderedDict()
                    result['Point'] = "{}, {}".format(cell_x, cell_y)
                    result['Value'] = attribute_ref[cell_x, cell_y]
                    result['Height'] = terrain_ref[cell_x, cell_y]

                    if self.flow_dir_data is not None:
                        flow_dir_ref = self.flow_dir_data.get_data(self.flow_dir_data.variables[0])
                        direction = flow_dir_ref[cell_x, cell_y]
                        result['Flow Direction (input)'] = direction
                        degrees = 45.0 + 45.0 * direction
                        result['Flow Direction (degrees)'] = degrees if degrees < 360.0 else degrees - 360.0

                    if self.flow_acc_data is not None:
                        result['Flow Accumulation'] = self.flow_acc_data.get_data(
                            self.flow_acc_data.variables[0]
                        )[cell_x, cell_y]

                    self.selected_point = (cell_x, cell_y)
                    self._needs_boundaries = True
                    self.refresh()

                    return result

        self.selected_point = (-1, -1)
        self._needs_boundaries = True
        self.refresh()

        return None
