"""
FeatureCollection - renders out features based on their shape type.
"""

import os

import mercantile
import numpy
import shapely.geometry as geometry
from OpenGL.GL import *
from pyproj import Proj, transform
from shapely.ops import triangulate

from vistas.core.gis.elevation import ElevationService
from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.mesh import Mesh
from vistas.core.graphics.renderable import Renderable
from vistas.core.graphics.shader import ShaderProgram
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

    def pre_render(self, camera):
        super().pre_render(camera)
        glBindVertexArray(self.feature.vertex_array_object)

    def post_render(self, camera):
        glBindVertexArray(0)
        super().post_render(camera)


class FeatureMesh(Mesh):

    def __init__(self, vertices, indices):
        super().__init__(len(indices), len(vertices), mode=Mesh.TRIANGLES)

        # Allocate buffers for this mesh
        vert_buf = self.acquire_vertex_array()
        vert_buf[:] = vertices.ravel()
        self.release_vertex_array()

        index_buf = self.acquire_index_array()
        index_buf[:] = indices.ravel()
        self.release_index_array()
        # Todo - initialize color array with gray color

        self.bounding_box = BoundingBox(0, vertices[:, 1].min(), 0,
                                        vertices[:, 0].max(), vertices[:, 1].max(), vertices[:, 2].max())  # Todo - determine bounding box

        self.shader = FeatureShaderProgram()
        self.shader.feature = self

    def color_feature(self):
        pass    # Todo - color a polygon


class FeatureCollectionRenderThread(Thread):

    def __init__(self, collection, scene):
        super().__init__()
        self.collection = collection
        self.scene = scene
        self.task = Task("Rendering Feature Collection")

    def run(self):

        self.task.status = Task.RUNNING
        verts, indices = self.collection.generate_meshes(self.task, use_cache=False)
        # Todo - initialize the color array with a gray color, allow it to be accessed later on

        self.sync_with_main(self.collection.add_features_to_scene,
                            (verts, indices, self.scene), block=True)

        self.sync_with_main(post_redisplay, kwargs={'reset': True}, block=True)
        self.task.status = Task.COMPLETE


class FeatureRenderable(Renderable):
    def __init__(self, vertices, indices):
        super().__init__()
        self.feature_mesh = FeatureMesh(vertices, indices)
        self.bounding_box = self.feature_mesh.bounding_box

    def render(self, camera):
        self.feature_mesh.shader.pre_render(camera)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.feature_mesh.index_buffer)
        glDrawElements(self.feature_mesh.mode, self.feature_mesh.num_indices, GL_UNSIGNED_INT, None)
        self.feature_mesh.shader.post_render(camera)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)


class FeatureCollection:
    """ An interface for handling large feature collections """

    def __init__(self, plugin, cellsize=30, zoom=10):
        self.renderable = None
        self.plugin = plugin
        self.extent = plugin.extent
        self.cellsize = cellsize

        self.zoom = zoom
        tiles = list(self.extent.tiles(self.zoom))
        self._ul = tiles[0]
        self._br = tiles[-1]

        self.bounding_box = BoundingBox(
            0, -10, 0,
            (self._br.x - self._ul.x + 1) * 256 * self.cellsize, 10, (self._br.y - self._ul.y + 1) * 256 * self.cellsize
        )

    def render(self, scene):
        """ Renders the feature collection into a given scene. """
        FeatureCollectionRenderThread(self, scene).start()

    def add_features_to_scene(self, vertices, indices, scene):
        self.renderable = FeatureRenderable(vertices, indices)
        self.renderable.bounding_box = self.bounding_box
        scene.add_object(self.renderable)

    @property
    def mercator_bounds(self):
        ul_bounds = mercantile.xy_bounds(self._ul)
        br_bounds = mercantile.xy_bounds(self._br)
        return mercantile.Bbox(ul_bounds.left, br_bounds.bottom, br_bounds.right, ul_bounds.top)

    def generate_meshes(self, task=None, use_cache=True):
        """ Generates polygon mesh vertices for a feature collection """
        # Todo - capture start-stop indices so coloring can happen on individual polygons via glBufferSubData access
        # This could be done by having a cache of indices, which can then be used properly with glBufferSubData

        vfile = self.plugin.path.replace('.shp', '.ttt')
        npz_path = vfile + '.npz'
        if use_cache and os.path.exists(npz_path):
            nfile = numpy.load(npz_path)
            verts, indices = nfile['verts'], nfile['indices']
            return verts, indices

        task.progress = 0
        task.target = self.plugin.get_num_features()

        mercator = self.extent.project(Proj(init='EPSG:3857')).projection
        mbounds = self.mercator_bounds
        e = ElevationService()

        # Get data DEM to sample elevation from
        dem, _ = e.create_data_dem(self.extent, self.zoom, merge=True)
        dheight, dwidth = dem.shape

        verts = None
        for feature in self.plugin.get_features():
            triangles = triangulate(geometry.shape(feature['geometry']))
            vertices = numpy.array([t.exterior.coords[:-1] for t in triangles], dtype=numpy.float32)
            xs, ys = transform(self.extent.projection, mercator, vertices[:, :, 0], vertices[:, :, 1])
            us = ((xs - mbounds.left) / (mbounds.right - mbounds.left))
            vs = (1 - (ys - mbounds.bottom) / (mbounds.top - mbounds.bottom))

            # Index into DEM to retrieve heights for each vertex
            try:
                heights = dem[numpy.floor(vs * dheight).astype(int), numpy.floor(us * dwidth).astype(int)].ravel()

            except IndexError:  # Todo - why does this index error happen?
                heights = numpy.zeros(us.shape, dtype=numpy.float32).ravel()

            # Move to world space
            us *= (self._br.x - self._ul.x + 1) * 256 * self.cellsize
            vs *= (self._br.y - self._ul.y + 1) * 256 * self.cellsize

            us = us.ravel()
            vs = vs.ravel()

            if verts is not None:
                new_verts = numpy.dstack((us, heights, vs))[0]
                verts = numpy.append(verts, new_verts, axis=0)
            else:
                verts = numpy.dstack((us, heights, vs))[0]

            if task:
                task.inc_progress()

        indices = numpy.arange(verts.shape[0])

        # cache the vertices and indices
        numpy.savez(vfile, verts=verts, indices=indices)
        return verts, indices
