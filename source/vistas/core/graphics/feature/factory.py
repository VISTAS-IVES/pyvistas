import os
from functools import partial

import numpy
import pyproj
import shapely.geometry as shp
from shapely.ops import transform
from triangle import triangulate

from vistas.core.color import RGBColor
from vistas.core.gis.elevation import ElevationService, TILE_SIZE, meters_per_px
from vistas.core.graphics.factory import MapMeshFactory, MeshFactoryWorker
from vistas.core.graphics.feature.geometry import FeatureGeometry
from vistas.core.graphics.feature.shader import FeatureShaderProgram
from vistas.core.graphics.mesh import Mesh
from vistas.core.plugins.data import FeatureDataPlugin


class FeatureFactoryWorker(MeshFactoryWorker):

    task_name = "Building Features"

    def work(self):
        verts, indices, normals, colors = [None] * 4
        if self.factory.needs_vertices and not self.task.should_stop:
            verts, indices, normals = self.factory.generate_meshes(self.task)
            self.factory.needs_vertices = False

        if self.factory.needs_color and not self.task.should_stop:
            colors = self.factory.generate_colors(self.task)
            self.factory.needs_color = False

        self.sync_with_main(
            self.factory.update_features, kwargs=dict(vertices=verts, indices=indices, normals=normals, colors=colors),
            block=True
        )


class FeatureFactory(MapMeshFactory):
    """ A MapMeshFactory for handling polygon rendering. """

    worker_class = FeatureFactoryWorker

    def __init__(self, extent, data_src: FeatureDataPlugin, shader=None, plugin=None, initial_zoom=10):
        super().__init__(extent, shader or FeatureShaderProgram(), plugin, initial_zoom)
        self._color_func = None
        self._render_thread = None

        if not isinstance(data_src, FeatureDataPlugin):
            raise TypeError("data_src is not of type FeatureDataPlugin!")
        self.data_src = data_src

        self.use_cache = self.data_src is not None
        if self.use_cache:
            self._cache = self.data_src.path.replace('.shp', '.ttt')
            self._npz_path = self._cache + '.npz'

        self.offsets = None
        self.needs_vertices = True
        self.needs_color = False

    @property
    def zoom(self):
        return self._zoom

    @zoom.setter
    def zoom(self, zoom):
        if zoom != self._zoom:
            self._zoom = zoom
            self.needs_vertices = True
            tiles = self.extent.tiles(self.zoom)
            self._ul = tiles[0]
            self._br = tiles[-1]
            self.build()

    def update_features(self, vertices=None, indices=None, normals=None, colors=None):
        # Update geometry information
        if vertices is not None and indices is not None and normals is not None:
            if not self.items:
                num_indices = num_vertices = len(indices)
                geometry = FeatureGeometry(num_indices, num_vertices, indices=indices, vertices=vertices)
                geometry.normals = normals
                mesh = Mesh(geometry, self.shader)
                self.items.append(mesh)
            else:
                mesh = self.items[0]
                geometry = mesh.geometry
                geometry.vertices = vertices
                geometry.indices = indices
                geometry.compute_bounding_box()
                mesh.update()
        # Update color buffer
        if self.items and colors is not None:
            self.items[0].geometry.colors = colors
        self.update()

    def generate_meshes(self, task=None):
        """ Generates polygon mesh vertices for a feature collection """

        mercator = pyproj.Proj(init='EPSG:3857')
        mbounds = self.mercator_bounds

        # Check if a cache for this feature exists
        if self.use_cache and os.path.exists(self._npz_path):
            if task:
                task.status = task.INDETERMINATE

            nfile = numpy.load(self._npz_path)
            verts = nfile['verts']

        # Build it out
        else:
            task.progress = 0
            task.target = self.data_src.get_num_features()

            project = partial(pyproj.transform, self.extent.projection, mercator)   # Our projection method

            tris = []
            offsets = []
            offset = 0
            for feature in self.data_src.get_features():
                shape = transform(project, shp.shape(feature['geometry']))
                if task:
                    task.inc_progress()

                if isinstance(shape, shp.Polygon):
                    polys = [list(shape.exterior.coords)[:-1]]
                elif isinstance(shape, shp.MultiPolygon):
                    polys = [list(p.exterior.coords)[:-1] for p in shape]
                else:
                    raise ValueError("Can't render non polygons!")

                for p in polys:
                    triangulation = triangulate(dict(vertices=numpy.array(p)))
                    t = triangulation.get('vertices')[triangulation.get('triangles')].reshape(-1, 2)
                    offset += t.size
                    tris.append(t)

                offsets.append(offset)

            triangles = numpy.concatenate(tris)
            offsets = numpy.array(offsets)

            # Make room for elevation info
            xs = triangles[:, 0]
            ys = triangles[:, 1]
            verts = numpy.dstack((ys, xs, numpy.zeros_like(xs)))[0]
            verts = verts.astype(numpy.float32)

            # cache the vertices
            if self.use_cache:
                numpy.savez(self._cache, verts=verts, offsets=offsets)

        # Translate vertices to scene coordinates
        # Scale vertices according to current mercator_bounds
        verts[:, 1] = (verts[:, 1] - mbounds.left) / (mbounds.right - mbounds.left)
        verts[:, 0] = (1 - (verts[:, 0] - mbounds.bottom) / (mbounds.top - mbounds.bottom))

        # Get data DEM to sample elevation from.
        e = ElevationService()
        dem = e.create_data_dem(self.extent, self.zoom, merge=True)
        dheight, dwidth = dem.shape

        # Index into current DEM and assign heights
        us = numpy.floor(verts[:, 1] * dwidth).astype(int)
        vs = numpy.floor(verts[:, 0] * dheight).astype(int)
        verts[:, 2] = dem[vs, us].ravel() / meters_per_px(self.zoom)

        # Scale vertices based on tile size
        verts[:, 0] *= (self._br.y - self._ul.y + 1) * TILE_SIZE
        verts[:, 1] *= (self._br.x - self._ul.x + 1) * TILE_SIZE

        normals = e.create_data_dem(
            self.extent, self.zoom, merge=True, src=ElevationService.AWS_NORMALS
        )[vs, us].ravel()

        # Vertex indices are assumed to be unique
        indices = numpy.arange(verts.shape[0])
        return verts, indices, normals

    @staticmethod
    def _default_color_function(feature, data):
        """
        Base color function for coloring features.
        :param feature: The feature to color
        :param data: Persistent data throughout the life of a single render
        :return: The RGBColor to color the feature
        """
        return RGBColor(0.5, 0.5, 0.5)

    def set_color_function(self, func):
        self._color_func = func

    def generate_colors(self, task=None):
        """ Generates a color buffer for the feature collection """

        # Color indices are stored in the cache
        if self.offsets is None:
            self.offsets = numpy.load(self._npz_path)['offsets']
        color_func = self._color_func
        if not color_func:
            color_func = self._default_color_function
        colors = []

        if task:
            task.progress = 0
            task.target = self.data_src.get_num_features()

        # We use a mutable data structure that is limited to this thread's scope and can be mutated
        # based on color_func's scope. This allows multiple color threads to occur without locking.
        mutable_color_data = {}
        for i, feature in enumerate(self.data_src.get_features()):
            if i == 0:
                left = 0
            else:
                left = self.offsets[i - 1]
            right = self.offsets[i]

            if task:
                if task.should_stop:
                    break
                task.inc_progress()

            num_vertices = (right - left) // 2
            color = numpy.array(color_func(feature, mutable_color_data).rgb.rgb_list, dtype=numpy.float32)
            for v in range(num_vertices):
                colors.append(color)
        colors = numpy.stack(colors)

        return colors


