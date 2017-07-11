from ctypes import sizeof, c_float

import numpy
import math
import shapely.geometry as geometry
from rasterio import features
from rasterio import transform
from collections import OrderedDict
from OpenGL.GL import *
from pyrr import Vector3, Vector4
from pyproj import transform as proj_transform

from vistas.core.color import RGBColor
from vistas.core.histogram import Histogram
from vistas.core.timeline import Timeline
from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.mesh import Mesh, MeshShaderProgram
from vistas.core.graphics.mesh_renderable import MeshRenderable
from vistas.core.graphics.vector_field_renderable import VectorFieldRenderable
from vistas.core.graphics.texture import Texture
from vistas.core.graphics.utils import map_buffer
from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.option import Option, OptionGroup
from vistas.core.plugins.visualization import VisualizationPlugin3D
from vistas.core.legend import Legend
from vistas.ui.utils import *


def normalize_v3(arr):
    """ Normalize a numpy array of 3 component vectors shape=(n,3) """

    lens = numpy.sqrt(arr[:, 0]**2 + arr[:, 1]**2 + arr[:, 2]**2)
    arr[:, 0] /= lens
    arr[:, 1] /= lens
    arr[:, 2] /= lens
    return arr


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

        self.heightfield = None
        self.normals = None

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

    def _get_attribute(self, option: Option):
        return option.labels[option.value]

    def update_option(self, option: Option=None):

        if option is None or option.plugin is not self:
            return

        name = option.name

        if name == self._attribute.name:
            self._needs_color = True
            stats = self.attribute_data.variable_stats(self._get_attribute(self._attribute))
            self._min_value.value = stats.min_value
            self._max_value.value = stats.max_value
            post_newoptions_available(self)

        elif name == self._elevation_attribute.name:
            self._needs_terrain = True

        elif name is self._boundary_width.name:
            self._needs_boundaries = True

        if self.flow_dir_data is not None:

            if name == self._animate_flow.name:
                self.vector_renderable.animate = self._animate_flow.value

            elif name == self._animation_speed.name:
                self.vector_renderable.animation_speed = self._animation_speed.value

            elif name == self._elevation_factor.name:
                self.vector_renderable.offset_multipliers = Vector3([1, self._elevation_factor.value, 1])

            elif name == self._flow_color.name:
                self.vector_renderable.color = self._flow_color.value

            elif name == self._flow_scale.name:
                self.vector_renderable.vector_scale = self._flow_scale.value

            elif name == self._show_flow.name:
                self.vector_renderable.visible = self._show_flow.value

            elif name == self._hide_no_data_vectors.name:
                self.vector_renderable.hide_no_data = self._hide_no_data_vectors.value

            elif name == self._acc_filter.name:
                self.vector_renderable.use_mag_filter = \
                    self._acc_filter.value and self.flow_acc_data is not None

            elif name == self._vector_speed.name:
                self.vector_renderable.vector_speed = self._vector_speed.value

            elif name in [self._acc_min.name, self._acc_max.name]:
                self.vector_renderable.mag_min = self._acc_min.value
                self.vector_renderable.mag_max = self._acc_max.value

            elif name == self._acc_scale.name:
                self.vector_renderable.use_magnitude_scale = \
                    self._acc_scale.value and self.flow_acc_data is not None

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
                self._min_value.value = stats.min_value
                self._max_value.value = stats.max_value
                self._attribute.value = 0
                self._attribute.labels = data.variables
            else:
                self._min_value.value, self._max_value.value = 0, 0
                self._attribute.labels = []
            post_newoptions_available(self)

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
        return self.attribute_data is not None

    @property
    def is_filtered(self):
        return self._is_filtered

    @property
    def filter_histogram(self):
        if self.attribute_data is not None:
            return Histogram(self.attribute_data.get_data(self._get_attribute(self._attribute), Timeline.app().current))
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

            if self.vector_renderable is not None:
                self._scene.remove_object(self.vector_renderable)

        self._scene = scene

        if self.mesh_renderable is not None and self._scene is not None:
            self._scene.add_object(self.mesh_renderable)

        if self.vector_renderable is not None and self._scene is not None:
            self._scene.add_object(self.vector_renderable)

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
            elevation_attribute = self._get_attribute(self._elevation_attribute)
            height_stats = self.terrain_data.variable_stats(elevation_attribute)
            nodata_value = height_stats.nodata_value
            min_value = height_stats.min_value
            max_value = height_stats.max_value
            cellsize = self.terrain_data.resolution
            height_data = self.terrain_data.get_data(elevation_attribute)
            if type(height_data) is numpy.ma.MaskedArray:
                height_data = height_data.data

            factor = 1.0
            height, width = height_data.shape

            num_indices = (height - 1) * width * 2 + ((height - 1) * 2 - 2)
            num_vertices = width * height

            max_height = math.sqrt(width * height * cellsize) / 2
            if max_value > max_height:
                factor = max_height / max_value

            # Compute heightfield and keep it to use for vector_renderable
            heightfield = numpy.zeros((height, width, 3))
            indices = numpy.indices((height, width))
            heightfield[:, :, 0] = indices[0] * cellsize   # x
            heightfield[:, :, 2] = indices[1] * cellsize   # z
            heightfield[:, :, 1] = height_data
            heightfield[:, :, 1][heightfield[:, :, 1] != nodata_value] *= factor    # Apply factor where needed
            heightfield[:, :, 1][heightfield[:, :, 1] == nodata_value] = min_value  # Otherwise, set to min value

            self.heightfield = heightfield

            mesh = Mesh(num_indices, num_vertices, True, True, True, mode=Mesh.TRIANGLE_STRIP)

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

            # Compute normals and keep them for using in vector_renderable
            normals = self._compute_normals(heightfield, index_array)
            self.normals = normals

            # Set mesh vertex array to heightfield
            vert_buf = mesh.acquire_vertex_array()
            vert_buf[:] = heightfield.ravel()
            mesh.release_vertex_array()

            # Set mesh normal array
            norm_buf = mesh.acquire_normal_array()
            norm_buf[:] = normals.ravel()
            mesh.release_normal_array()

            # Set mesh index array
            index_buf = mesh.acquire_index_array()
            index_buf[:] = index_array
            mesh.release_index_array()

            # Set mesh texture coordinates
            texcoord_buf = mesh.acquire_texcoords_array()
            tex_coords = numpy.zeros((height, width, 2))
            tex_coords[:, :, 0] = indices[0] / height  # u
            tex_coords[:, :, 1] = 1 - indices[1] / width   # v
            texcoord_buf[:] = tex_coords.ravel()
            mesh.release_texcoords_array()

            mesh.bounding_box = BoundingBox(0, min_value * factor, 0,
                                            height * cellsize, max_value * factor, width * cellsize)

            self.mesh_renderable = TerrainRenderable(mesh)
            self.mesh_renderable.plugin = self
            self._scene.add_object(self.mesh_renderable)

            self._update_terrain_color()
        else:
            if self.mesh_renderable is not None:
                self._scene.remove_object(self.mesh_renderable)
                self.mesh_renderable = None

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
        return norm.reshape(heightfield.shape)

    def _update_terrain_color(self):

        if self.mesh_renderable is not None:
            shader = self.mesh_renderable.mesh.shader

            if self.terrain_data and self.attribute_data:
                shader.has_color = True

                # Retrieve color layer
                attribute = self._get_attribute(self._attribute)
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

        if self.mesh_renderable is None:
            return

        shader = self.mesh_renderable.mesh.shader

        if self.terrain_data is not None:
            shader.has_boundaries = True

            # Create boundary image
            texture_w, texture_h = 512, 512
            image_data = numpy.ones((texture_h, texture_w, 3), dtype=numpy.uint8) * 255

            terrain_extent = self.terrain_data.extent

            if self.boundary_data is not None:

                # Burn geometry to texture
                shapes = self.boundary_data.get_features()
                image_data[:, :, 0] = numpy.flipud(features.rasterize(
                    [geometry.shape(f['geometry']).exterior for f in shapes if f['geometry']['type'] == 'Polygon'],
                    out_shape=(texture_h, texture_w), fill=255, default_value=0,
                    transform=transform.from_bounds(*terrain_extent.as_list(), texture_w, texture_h)
                ))

            if self.selected_point != (-1, -1):
                p = self.selected_point
                cell_size = self.terrain_data.resolution
                grid_width, grid_height = self.terrain_data.shape
                xscale = texture_w / terrain_extent.width
                yscale = texture_h / terrain_extent.height
                box_w, box_h = cell_size * xscale, cell_size * yscale
                center = (int(p[0] / grid_height * texture_w), int(512 - p[1] / grid_width * texture_h))

                # Draw black rectangle directly into data
                min_x = center[0] - box_w / 2
                min_x = min_x if min_x >= 0 else 0
                max_x = center[0] + box_w / 2
                max_x = max_x if max_x <= 511 else 511
                min_y = center[1] - box_h / 2
                min_y = min_y if min_y >= 0 else 0
                max_y = center[1] + box_h / 2
                max_y = max_y if max_y <= 511 else 511

                image_data[round(min_y): round(max_y), round(min_x): round(max_x), 0] = 0

            shader.boundary_texture = Texture(data=image_data.ravel(), width=texture_w, height=texture_h)
        else:
            shader.has_boundaries = False
            shader.boundary_texture = Texture()

    def _update_flow(self):

        if self.terrain_data is not None and self.flow_dir_data is not None:

            height_label = self._get_attribute(self._elevation_attribute)
            flow_dir_label = self.flow_dir_data.variables[0]
            flow_acc_label = self.flow_acc_data.variables[0] if self.flow_acc_data is not None else ""
            attribute_label = self._get_attribute(self._attribute)

            height_data = self.terrain_data.get_data(height_label, Timeline.app().current)
            flow_dir = self.flow_dir_data.get_data(flow_dir_label, Timeline.app().current)

            height, width = flow_dir.shape

            if not flow_dir.shape == height_data.shape:
                post_message("Terrain and flow grids don't match. Did you load the correct flow grid for this terrain?",
                             MessageEvent.ERROR)
                return

            # Clobber all the data into one big array
            vector_data = numpy.zeros((height, width, 7), dtype=numpy.float32)
            vector_data[:, :, 0:3] = self.heightfield
            vector_data[:, :, 3] = flow_dir * -45.0 + 45.0       # VELMA flow direction, converted to polar degrees
            vector_data[:, :, 4] = numpy.zeros((height, width), dtype=numpy.float32)   # tilt of vector
            vector_data[:, :, 4] = 90 - numpy.arcsin(numpy.abs(self.normals[:, :, 1])) * 180 / numpy.pi
            vector_data[:, :, 5] = numpy.ones((height, width), dtype=numpy.float32) if self.flow_acc_data is None else \
                self.flow_acc_data.get_data(flow_acc_label, Timeline.app().current)
            vector_data[:, :, 6] = numpy.zeros((height, width), dtype=numpy.float32) if self.attribute_data is None \
                else self.attribute_data.get_data(attribute_label, Timeline.app().current)

            # Inform vector_renderable of attribute grid (if set) so shader knows whether to hide nodata values
            if self.attribute_data is not None:
                nodata_value = self.attribute_data.variable_stats(attribute_label).nodata_value
            else:
                nodata_value = 1.0

            if self.vector_renderable is None:
                self.vector_renderable = VectorFieldRenderable(data=vector_data)
                self.scene.add_object(self.vector_renderable)
            else:
                self.vector_renderable.set_vector_data(vector_data)

            self.vector_renderable.nodata_value = nodata_value
            self.vector_renderable.use_mag_filter = self._acc_filter.value and self.flow_acc_data is not None
            self.vector_renderable.mag_min = self._acc_min.value
            self.vector_renderable.mag_max = self._acc_max.value
            self.vector_renderable.use_magnitude_scale = self._acc_scale.value and self.flow_acc_data is not None
            self.vector_renderable.visible = self._show_flow.value

        elif self.vector_renderable is not None:
            self.vector_renderable.visible = False

    def has_legend(self):
        return self.attribute_data is not None

    def get_legend(self, width, height):
        return Legend.stretched(
            width, height, self._min_value.value, self._max_value.value, self._min_color.value, self._max_color.value
        )


class TerrainRenderable(MeshRenderable):
    def __init__(self, mesh=None):
        super().__init__(mesh)
        self.plugin = None

    @property
    def selection_shader(self):
        shader = TerrainAndColorShaderProgram(self.mesh)
        shader.attach_shader(self.plugin.get_shader_path('selection_vert.glsl'), GL_VERTEX_SHADER)
        shader.height_factor = self.plugin._elevation_factor.value if self.plugin._elevation_factor.value > 0 else 0.01
        return shader

    def get_selection_detail(self, width, height, x, y, camera):

        device_x = x * 2.0 / width - 1
        device_y = 1 - 2.0 * y / height

        ray_clip = Vector4([device_x, device_y, -1, 1])
        ray_eye = camera.proj_matrix.inverse * ray_clip
        ray_eye = Vector4([ray_eye.x, ray_eye.y, -1.0, 1.0])

        ray_world = (camera.matrix.T * ray_eye).vector3[0]
        ray_world.normalise()

        bbox = self.mesh.bounding_box
        v1 = Vector3([bbox.min_x, bbox.min_y, bbox.min_z])
        v2 = Vector3([bbox.max_x, bbox.min_y, bbox.min_z])
        v3 = Vector3([bbox.min_x, bbox.min_y, bbox.max_z])
        plane_normal = ((v2 - v1).cross(v3 - v1))
        plane_normal.normalise()

        camera_pos = camera.get_position()
        denom = ray_world.dot(plane_normal)

        if abs(denom) > 1e-6:

            d = (v1 - Vector3()).length

            t = -((camera_pos.dot(plane_normal) + d ) / denom)

            terrain_ref = self.plugin.terrain_data.get_data(self.plugin._get_attribute(self.plugin._elevation_attribute))
            terrain_stats = self.plugin.terrain_data.variable_stats("")
            res = self.plugin.terrain_data.resolution
            nodata_value = terrain_stats.nodata_value
            width, height = terrain_ref.shape
            min_height_value = terrain_stats.min_value
            max_height_value = terrain_stats.max_value
            factor = 1.0
            elevation_multiplier = self.plugin._elevation_factor.value

            max_height = numpy.sqrt(width * height * res) / 2
            if max_height_value > max_height:
                factor = max_height / max_height_value

            point = ray_world * t + camera_pos
            cell_x = int(round((point.x - v1.x) / res))
            cell_y = int(round((point.z - v1.z) / res))

            angle = numpy.arcsin(camera_pos.y / t)
            step = res / numpy.cos(angle)

            t2 = 0
            while t2 < t:

                p = ray_world * t2 + camera_pos
                x = int(round((p.x - v1.x) / res))
                y = int(round((p.z - v1.z) / res))

                if x >= 0 and x < width and y >= 0 and y < height:
                    cell_height = terrain_ref[x, y]
                    cell_height = cell_height * factor if cell_height != nodata_value else min_height_value
                    cell_height *= elevation_multiplier

                    if cell_height >= p.y:
                        cell_x = x
                        cell_y = y
                        break

                t2 += step

            if self.plugin.attribute_data is not None:

                attribute_ref = self.plugin.attribute_data.get_data(self.plugin._get_attribute(self.plugin._attribute))
                attr_width, attr_height = attribute_ref.shape
                if 0 <= cell_x < attr_width and 0 <= cell_y < attr_height:

                    result = OrderedDict()
                    result['Point'] = "{}, {}".format(cell_x, cell_y)
                    result['Value'] = attribute_ref[cell_x, cell_y],
                    result['Height'] = terrain_ref[cell_x, cell_y]

                    if self.plugin.flow_dir_data is not None:
                        flow_dir_ref = self.plugin.flow_dir_data.get_data("")
                        direction = flow_dir_ref[cell_x, cell_y]
                        result['Flow Direction (input)'] = direction
                        degrees = 45.0 + 45.0 * direction
                        result['Flow Direction (degrees)'] = degrees if degrees < 360.0 else degrees - 360.0

                    if self.plugin.flow_acc_data is not None:
                        result['Flow Accumulation'] = self.plugin.flow_acc_data.get_data("")[cell_x, cell_y]

                    self.plugin.selected_point = (cell_x, cell_y)
                    self.plugin._needs_boundaries = True
                    self.plugin.refresh()

                    return result

        self.plugin.selected_point = (-1, -1)
        self.plugin.needs_boundaries = True
        self.plugin.refresh()

        return None


class TerrainAndColorShaderProgram(MeshShaderProgram):
    def __init__(self, mesh):
        super().__init__(mesh)

        self.value_buffer = glGenBuffers(1)

        tw, th = 512, 512
        img_data = (numpy.ones((tw, th, 3)).astype(numpy.uint8) * 255).ravel()
        img_data = img_data.ravel()
        self.boundary_texture = Texture(data=img_data, width=tw, height=tw)

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
            glEnableVertexAttribArray(value_loc)
            glVertexAttribPointer(value_loc, 1, GL_FLOAT, GL_FALSE, sizeof(GLfloat), None)
            glBindBuffer(GL_ARRAY_BUFFER, 0)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.boundary_texture.texture)
        self.uniform1i("boundaryTexture", 0)

        self.uniform1i("hideNoData", self.hide_no_data)
        self.uniform1i("perVertexColor", self.per_vertex_color)
        self.uniform1i("perVertexLighting", self.per_vertex_lighting)
        self.uniform1i("hasColor", self.has_color)
        self.uniform1i("hasBoundaries", self.has_boundaries)

        self.uniform1i("isFiltered", self.is_filtered)
        self.uniform1f("filterMin", self.filter_min)
        self.uniform1f("filterMax", self.filter_max)

        self.uniform1f("heightFactor", self.height_factor)
        self.uniform1f("noDataValue", self.nodata_value)
        self.uniform1f("minValue", self.min_value)
        self.uniform1f("maxValue", self.max_value)
        self.uniform4fv("minColor", 1, self.min_color)
        self.uniform4fv("maxColor", 1, self.max_color)
        self.uniform4fv("noDataColor", 1, self.nodata_color)
        self.uniform4fv("boundaryColor", 1, self.boundary_color)

    def post_render(self, camera):
        glBindTexture(GL_TEXTURE_2D, 0)
        super().post_render(camera)
