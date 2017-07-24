"""
FeatureCollectionRenderable - renders out features based on their shape type.

Features will be rendered out according to a
"""

import os
import mercantile
import numpy
from OpenGL.GL import *
from pyproj import Proj, transform
from pyrr import Vector3, Matrix44
from pyrr.vector3 import generate_vertex_normals
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
from vistas.ui.utils import post_redisplay


class FeatureShaderProgram(ShaderProgram):
    """ The most basic shader class for coloring features. """

    _tile_shader = None

    @classmethod
    def get(cls):
        if cls._tile_shader is None:
            cls._tile_shader = FeatureShaderProgram()
        return cls._tile_shader

    def __init__(self):
        super().__init__()
        self.current_feature = None
        self.attach_shader(os.path.join(get_resources_directory(), 'shaders', 'feature_vert.glsl'), GL_VERTEX_SHADER)
        self.attach_shader(os.path.join(get_resources_directory(), 'shaders', 'feature_frag.glsl'), GL_FRAGMENT_SHADER)
        self.link_program()

    def pre_render(self, camera):
        if self.current_feature:
            super().pre_render(camera)
            glBindVertexArray(self.current_feature.vertex_array_object)

    def post_render(self, camera):
        if self.current_feature:
            glBindVertexArray(0)
            super().post_render(camera)


class FeatureMesh(Mesh):

    def __init__(self, vertices):

        # Determine number of vertices and indices, which really are the same
        num_vertices = len(vertices)
        num_indices = num_vertices
        super().__init__(num_indices, num_vertices, True)
        indices = numpy.arange(num_indices, dtype='uint8')
        faces = numpy.array([indices[i:i+3] for i in range(len(indices) - 2)])

        normals = generate_vertex_normals(vertices, faces).ravel()

        vert_buf = self.acquire_vertex_array()
        vert_buf[:] = vertices.ravel()
        self.release_vertex_array()

        norm_buf = self.acquire_normal_array()
        norm_buf[:] = normals.ravel()
        self.release_normal_array()

        index_buf = self.acquire_index_array()
        index_buf[:] = indices.ravel()
        self.release_index_array()

        self.bounding_box = BoundingBox(0, -10, 0, 10, 10, 10)  # Todo - determine bounding box

        self.shader = FeatureShaderProgram.get()


class FeatureCollectionRenderThread(Thread):

    def __init__(self, collection):
        super().__init__()
        self.collection = collection
        self.task = Task("Rendering Feature Collection")

    def run(self):

        self.task.target = len(self.collection.features)
        self.task.status = Task.RUNNING
        _verts = None
        for vertices in self.collection.generate_meshes():
            if _verts is None:
                _verts = vertices
            else:
                numpy.vstack((_verts, vertices))
            self.task.inc_progress()
        self.sync_with_main(self.collection.add_feature_renderable,
                            (_verts, True), block=True)
            #
        self.collection.can_render = True
        self.sync_with_main(post_redisplay, kwargs={'reset': True}, block=True)
        self.task.status = Task.COMPLETE


class FeatureRenderable(Renderable):
    def __init__(self, vertices=None):
        super().__init__()
        self.feature_mesh = FeatureMesh(vertices)
        self.bounding_box = self.feature_mesh.bounding_box

    def render(self, camera):
        if self.feature_mesh:
            self.feature_mesh.shader.current_feature = self.feature_mesh    # take ownership of the shader's render target
            self.feature_mesh.shader.pre_render(camera)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.feature_mesh.index_buffer)
            glDrawElements(self.feature_mesh.mode, self.feature_mesh.num_indices, GL_UNSIGNED_INT, None)
            self.feature_mesh.shader.post_render(camera)
            self.feature_mesh.shader.current_feature = None    # now let it go
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)



class FeatureCollection:
    """ An interface for handling large feature collections """

    def __init__(self, features, extent, mercator_bounds, cellsize):
        self.features = [geometry.shape(f['geometry']) for f in features]
        self.renderables = []
        self.extent = extent
        self.mercator_bounds = mercator_bounds
        self.cellsize = cellsize
        self.can_render = False


        _meshes = [m for m in self.generate_meshes()]
        data = _meshes[0]
        for i in range(1, len(_meshes)):
            data = numpy.append(data, _meshes[i], axis=0)
        self.add_feature_renderable(data, None)

#        for mesh in self.generate_meshes():
#            self.add_feature_renderable(mesh,None)
#        self.can_render = True

        #FeatureCollectionRenderThread(self).start()

    def add_feature_renderable(self, vertices, nothing):
        self.renderables.append(FeatureRenderable(vertices))

    def grid_coords(self, coords):  # Assumed to be in mercator
        bounds = self.mercator_bounds
        grid_coords = []
        for x, y in coords:
            u = (x - bounds.left) / (bounds.right - bounds.left)
            v = 1 - (y - bounds.bottom) / (bounds.top - bounds.bottom)
            grid_coords.append((u * 256 * self.cellsize, v * 256 * self.cellsize))
        return grid_coords

    def generate_meshes(self):
        """ Yields one set of vertices for each feature """
        mercator = self.extent.project(Proj(init='EPSG:3857')).projection
        bounds = self.mercator_bounds
        meshes = []
        for shp in self.features:
            triangles = triangulate(geometry.shape(shp))     # list of shapely.geometry.Polygons
            vertices = []
            for tri in triangles:
                tri_coords = tri.exterior.coords
                scene_coords = []
                for x, y in tri_coords[:-1]:    # last coord is a repeat, OpenGL finishes the triangle for us

                    # project triangle coordinates to mercator
                    _x, z = transform(self.extent.projection, mercator, x, y)
                    y = 0   # Todo - obtain elevation for z from elevation grid

                    # now convert mercator to scene coordinates
                    u = (_x - bounds.left) / (bounds.right - bounds.left) * 256 * self.cellsize
                    v = (1 - (z - bounds.bottom) / (bounds.top - bounds.bottom)) * 256 * self.cellsize

                    scene_coords += [u, y, v]
                vertices += scene_coords
            meshes.append(numpy.array(vertices, dtype=numpy.float32).reshape(-1, 3))
        return meshes

    def _to_scene_coords(self, coords):  # Assumed to be in mercator
        bounds = self.mercator_bounds
        scene_coords = []
        for x, y, z in coords:
            u = (x - bounds.left) / (bounds.right - bounds.left)
            v = 1 - (z - bounds.bottom) / (bounds.top - bounds.bottom)
            scene_coords.append((u * 256 * self.cellsize, y, v * 256 * self.cellsize))
        return scene_coords

    def transfer_to_scene(self, scene):
        for r in self.renderables:
            scene.add_object(r)

    def remove_from_scene(self, scene):
        pass
