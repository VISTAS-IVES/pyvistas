import os
from functools import partial

import mercantile
import numpy
import pyproj
import shapely.geometry as geometry
import triangle
from OpenGL.GL import *
from shapely.ops import transform

from vistas.core.color import RGBColor
from vistas.core.gis.elevation import ElevationService
from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.mesh import Mesh
from vistas.core.graphics.renderable import Renderable
from vistas.core.graphics.shader import ShaderProgram
from vistas.core.graphics.tile import TILE_SIZE, calculate_cellsize
from vistas.core.paths import get_resources_directory
from vistas.core.task import Task
from vistas.core.threading import Thread
from vistas.ui.utils import post_redisplay


class FeatureShaderProgram(ShaderProgram):
    """ The most basic shader class for coloring features. """

    def __init__(self):
        super().__init__()
        self.feature = None
        self.attach_shader(os.path.join(get_resources_directory(), 'shaders', 'feature_vert.glsl'), GL_VERTEX_SHADER)
        self.attach_shader(os.path.join(get_resources_directory(), 'shaders', 'feature_frag.glsl'), GL_FRAGMENT_SHADER)
        self.link_program()
        self.alpha = 1.0
        self.height_multiplier = 1.0
        self.height_offset = 500.0

    def pre_render(self, camera):
        super().pre_render(camera)

        # Set shader uniforms for features
        self.uniform1f('alpha', self.alpha)
        self.uniform1f('heightMultiplier', self.height_multiplier)
        self.uniform1f('heightOffset', self.height_offset)

        glBindVertexArray(self.feature.vertex_array_object)

    def post_render(self, camera):
        glBindVertexArray(0)
        super().post_render(camera)


class FeatureMesh(Mesh):

    def __init__(self, vertices, indices):
        super().__init__(len(indices), len(vertices), has_color_array=True, mode=Mesh.TRIANGLES)

        color_buf = self.acquire_color_array()
        color_buf[:] = numpy.ones_like(vertices.ravel()) * 0.5  # init the color buffer with grey
        self.release_color_array()

        self.shader = FeatureShaderProgram()
        self.shader.feature = self


class FeatureCollectionRenderThread(Thread):

    def __init__(self, collection, scene):
        super().__init__()
        self.collection = collection
        self.scene = scene
        self.task = Task("Rendering feature collection")

    def run(self):
        self.init_event_loop()

        if self.collection.needs_vertices:
            self.task.status = Task.RUNNING
            self.task.name = 'Generating meshes'
            verts, indices = self.collection.generate_meshes(self.task)
            self.sync_with_main(self.collection.add_features_to_scene, (verts, indices, self.scene), block=True)
            self.collection.needs_vertices = False

        if self.collection.needs_color:
            self.task.status = Task.RUNNING
            self.task.name = 'Coloring meshes'
            colors = self.collection.generate_colors(self.task)
            self.sync_with_main(self.collection.color_features, (colors, None), block=True)
            self.collection.needs_color = False

        self.sync_with_main(post_redisplay)
        self.task.status = Task.COMPLETE


class FeatureRenderable(Renderable):
    def __init__(self, vertices, indices):
        super().__init__()
        self.mesh = FeatureMesh(vertices, indices)
        self.bounding_box = self.mesh.bounding_box

    def render(self, camera):
        self.mesh.shader.pre_render(camera)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.mesh.index_buffer)
        glDrawElements(self.mesh.mode, self.mesh.num_indices, GL_UNSIGNED_INT, None)
        self.mesh.shader.post_render(camera)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

    @property
    def transparency(self):
        return self.mesh.shader.alpha

    @transparency.setter
    def transparency(self, alpha):
        """ Set the transparency of the feature layer. """

        if alpha > 1.0:
            alpha = 1.0
        elif alpha < 0.0:
            alpha = 0.0
        self.mesh.shader.alpha = alpha

    @property
    def height_multiplier(self):
        return self.mesh.shader.height_multiplier

    @height_multiplier.setter
    def height_multiplier(self, multiplier):
        self.mesh.shader.height_multiplier = multiplier

    @property
    def height_offset(self):
        return self.mesh.shader.height_offset

    @height_offset.setter
    def height_offset(self, offset):
        self.mesh.shader.height_offset = offset


class FeatureLayer:
    """ An interface for handling feature collection rendering """

    def __init__(self, plugin, zoom=10):
        self.renderable = None
        self.plugin = plugin
        self.extent = plugin.extent

        self._ul = None
        self._br = None
        self.bounding_box = None
        self._zoom = None
        self.cellsize = None
        self.zoom = zoom    # update bounds

        self._color_func = None

        self._cache = self.plugin.path.replace('.shp', '.ttt')
        self._npz_path = self._cache + '.npz'

        self.needs_vertices = True
        self.needs_color = True

    @property
    def zoom(self):
        return self._zoom

    @zoom.setter
    def zoom(self, zoom):
        self._zoom = zoom
        self.needs_vertices = True
        tiles = list(self.extent.tiles(self.zoom))
        self._ul = tiles[0]
        self._br = tiles[-1]

        self.cellsize = calculate_cellsize(self.zoom)

        self.bounding_box = BoundingBox(
            0, -10, 0,
            (self._br.x - self._ul.x + 1) * TILE_SIZE * self.cellsize, 10, (self._br.y - self._ul.y + 1) * TILE_SIZE * self.cellsize
        )
        if self.renderable:
            self.renderable.bounding_box = self.bounding_box

    def render(self, scene):
        """ Renders the feature collection into a given scene. """

        FeatureCollectionRenderThread(self, scene).start()

    def add_features_to_scene(self, vertices, indices, scene):
        """ Render callback to add the the feature collection's renderable to the specified scene. """

        if self.renderable is None:
            self.renderable = FeatureRenderable(vertices, indices)
            scene.add_object(self.renderable)

        # Allocate buffers for this mesh
        mesh = self.renderable.mesh
        vert_buf = mesh.acquire_vertex_array()
        vert_buf[:] = vertices.ravel()
        mesh.release_vertex_array()

        index_buf = mesh.acquire_index_array()
        index_buf[:] = indices.ravel()
        mesh.release_index_array()

        self.renderable.bounding_box = self.bounding_box

    def color_features(self, colors, _=None):
        """ Coloring callback to set the colors of the feature collection. """

        if self.renderable is not None:
            color_buf = self.renderable.mesh.acquire_color_array()
            color_buf[:] = colors.ravel()
            self.renderable.mesh.release_color_array()

    @property
    def mercator_bounds(self):
        """ The zxy tile (mercator) bounds of the feature collection. """

        ul_bounds = mercantile.xy_bounds(self._ul)
        br_bounds = mercantile.xy_bounds(self._br)
        return mercantile.Bbox(ul_bounds.left, br_bounds.bottom, br_bounds.right, ul_bounds.top)

    @property
    def geographic_bounds(self):
        """ The geographic bounds of the underlying tiles of the feature collection. """

        ul_bounds = mercantile.bounds(self._ul)
        br_bounds = mercantile.bounds(self._br)
        return mercantile.LngLatBbox(ul_bounds.west, br_bounds.south, br_bounds.east, ul_bounds.north)

    def generate_meshes(self, task=None, use_cache=True):
        """ Generates polygon mesh vertices for a feature collection """

        mercator = pyproj.Proj(init='EPSG:3857')
        mbounds = self.mercator_bounds

        # Check if a cache for this collection exists
        if use_cache and os.path.exists(self._npz_path):
            if task:
                task.name = 'Loading meshes from cache'
                task.status = task.INDETERMINATE

            nfile = numpy.load(self._npz_path)
            verts = nfile['verts']

        # Build it out
        else:
            task.progress = 0
            task.target = self.plugin.get_num_features()

            project = partial(pyproj.transform, self.extent.projection, mercator)   # Our projection method

            tris = []
            offsets = []
            offset = 0
            for i, feature in enumerate(self.plugin.get_features()):
                shape = transform(project, geometry.shape(feature['geometry']))
                if task:
                    task.inc_progress()

                if isinstance(shape, geometry.Polygon):
                    polys = [list(shape.exterior.coords)[:-1]]
                elif isinstance(shape, geometry.MultiPolygon):
                    polys = [list(p.exterior.coords)[:-1] for p in shape]
                else:
                    raise ValueError("Can't render non polygons!")

                for p in polys:
                    triangulation = triangle.triangulate(dict(vertices=numpy.array(p)))
                    t = triangulation.get('vertices')[triangulation.get('triangles')].reshape(-1, 2)
                    offset += t.size
                    tris.append(t)

                offsets.append(offset)

            triangles = numpy.concatenate(tris)
            offsets = numpy.array(offsets)

            # Make room for elevation info
            xs = triangles[:, 0]
            ys = triangles[:, 1]
            verts = numpy.dstack((xs, numpy.zeros_like(xs), ys))[0]

            # cache the vertices
            if use_cache:
                numpy.savez(self._cache, verts=verts, offsets=offsets)

        # Translate vertices to scene coordinates
        # Scale vertices according to current mercator_bounds
        verts[:, 0] = (verts[:, 0] - mbounds.left) / (mbounds.right - mbounds.left)
        verts[:, 2] = (1 - (verts[:, 2] - mbounds.bottom) / (mbounds.top - mbounds.bottom))

        # Get data DEM to sample elevation from.
        e = ElevationService()
        dem = e.create_data_dem(self.extent, self.zoom, merge=True)
        dheight, dwidth = dem.shape

        # Index into current DEM and assign heights
        us = numpy.floor(verts[:, 0] * dwidth).astype(int)
        vs = numpy.floor(verts[:, 2] * dheight).astype(int)
        verts[:, 1] = dem[vs, us].ravel()

        # Scale vertices based on tile size
        verts[:, 0] *= (self._br.x - self._ul.x + 1) * TILE_SIZE * self.cellsize
        verts[:, 2] *= (self._br.y - self._ul.y + 1) * TILE_SIZE * self.cellsize

        # Vertex indices are assumed to be unique
        indices = numpy.arange(verts.shape[0])

        return verts, indices

    @staticmethod
    def _default_color_function(feature):
        return RGBColor(0.5, 0.5, 0.5)

    def set_color_function(self, func, needs_color=True):
        self._color_func = func
        self.needs_color = needs_color

    def generate_colors(self, task=None):
        """ Generates a color buffer for the feature collection """

        # Color indices are stored in the cache
        offsets = numpy.load(self._npz_path)['offsets']
        color_func = self._color_func
        if not color_func:
            color_func = self._default_color_function
        colors = []

        if task:
            task.progress = 0
            task.target = self.plugin.get_num_features()

        for i, feature in enumerate(self.plugin.get_features()):
            if i == 0:
                left = 0
            else:
                left = offsets[i - 1]
            right = offsets[i]

            if task:
                task.inc_progress()

            num_vertices = (right - left) // 2
            color = numpy.array(color_func(feature).rgb.rgb_list, dtype=numpy.float32)
            for v in range(num_vertices):
                colors.append(color)

        colors = numpy.stack(colors)

        return colors

