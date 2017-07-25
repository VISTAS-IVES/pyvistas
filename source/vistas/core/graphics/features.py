"""
FeatureCollection - renders out features based on their shape type.
"""

import os
import mercantile
import numpy
from OpenGL.GL import *
from pyproj import Proj, transform
import shapely.geometry as geometry
from shapely.ops import triangulate
from vistas.core.gis.elevation import ElevationService
from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.mesh import Mesh
from vistas.core.graphics.renderable import Renderable
from vistas.core.graphics.shader import ShaderProgram
from vistas.core.paths import get_resources_directory
from vistas.core.task import Task
from vistas.core.threading import Thread
from vistas.ui.utils import post_redisplay, post_message


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

        self.bounding_box = BoundingBox(0, -10, 0, 10, 10, 10)  # Todo - determine bounding box

        self.shader = FeatureShaderProgram()
        self.shader.feature = self


class FeatureCollectionRenderThread(Thread):

    def __init__(self, collection, scene):
        super().__init__()
        self.collection = collection
        self.scene = scene
        self.task = Task("Rendering Feature Collection")

    def run(self):

        self.task.status = Task.RUNNING
        verts, indices = self.collection.generate_meshes(self.task)  # Todo - look for optimizations
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

    def __init__(self, plugin, cellsize=30, zoom=10, tolerance=1):
        self.renderable = None
        self.plugin = plugin
        self.extent = plugin.extent
        self.cellsize = cellsize
        self.tolerance = tolerance  # geometry simplification tolerance

        self.zoom = zoom
        self.wgs84 = self.extent.project(Proj(init='EPSG:4326'))
        tiles = list(mercantile.tiles(*self.wgs84.as_list(), [self.zoom]))
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

    def generate_meshes(self, task=None):
        """ Generates polygon mesh vertices for a feature collection """

        vfile = self.plugin.path.replace('.shp', '.ttt')
        npz_path = vfile + '.npz'
        if os.path.exists(npz_path):
            nfile = numpy.load(npz_path)
            verts, indices = nfile['verts'], nfile['indices']
            return verts, indices

        task.progress = 0
        task.target = self.plugin.get_num_features() * 2

        mercator = self.extent.project(Proj(init='EPSG:3857')).projection
        mbounds = self.mercator_bounds
        e = ElevationService()
        meshes = []
        for feature in self.plugin.get_features():
            triangles = triangulate(geometry.shape(feature['geometry']).simplify(self.tolerance))
            vertices = []
            for tri in triangles:
                tri_coords = tri.exterior.coords
                scene_coords = []
                for x, y in tri_coords[:-1]:    # last coord is a repeat, OpenGL finishes the triangle for us

                    # project triangle coordinates to mercator
                    mx, my = transform(self.extent.projection, mercator, x, y)

                    # now convert mercator to scene coordinates
                    u = ((mx - mbounds.left) / (mbounds.right - mbounds.left))
                    v = (1 - (my - mbounds.bottom) / (mbounds.top - mbounds.bottom))

                    # Determine which tile we landed in and get the height at that value
                    lng, lat = transform(self.extent.projection, self.wgs84.projection, x, y)
                    t = mercantile.tile(lng, lat, self.zoom)
                    tbounds = mercantile.xy_bounds(t)
                    sx = int(numpy.floor((mx - tbounds.left) / (tbounds.right - tbounds.left) * 256))
                    sy = int(numpy.floor((1 - (my - tbounds.bottom) / (tbounds.top - tbounds.bottom)) * 256))
                    height = e.get_grid(t.x, t.y, self.zoom)[sy, sx]

                    # Translate to proper tile position
                    u *= (self._br.x - self._ul.x + 1) * 256 * self.cellsize
                    v *= (self._br.y - self._ul.y + 1) * 256 * self.cellsize

                    scene_coords += [u, height, v]
                vertices += scene_coords
            meshes.append(numpy.array(vertices, dtype=numpy.float32).reshape(-1, 3))

            if task:
                task.inc_progress()

        # Concatenate vertices and build indices
        verts = meshes[0]
        indices = numpy.arange(verts.size, dtype='uint8')
        for vertices in meshes[1:]:
            verts = numpy.append(verts, vertices, axis=0)
            indices = numpy.append(indices, numpy.arange(indices.size, indices.size + vertices.size))
            if task:
                task.inc_progress()

        # cache the vertices and indices
        numpy.savez(vfile, verts=verts, indices=indices)
        return verts, indices
