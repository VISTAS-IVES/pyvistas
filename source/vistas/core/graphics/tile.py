import asyncio
import os
import sys
from ctypes import c_float, c_uint, sizeof
import math

import mercantile
import numpy
from OpenGL.GL import *
from pyproj import Proj
from pyrr import Vector3, Matrix44
from pyrr.vector3 import generate_vertex_normals

from vistas.core.gis.elevation import ElevationService
from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.mesh import Mesh
from vistas.core.graphics.renderable import Renderable
from vistas.core.graphics.shader import ShaderProgram
from vistas.core.graphics.utils import map_buffer
from vistas.core.paths import get_resources_directory
from vistas.core.task import Task
from vistas.core.threading import Thread
from vistas.ui.utils import post_redisplay


class TileShaderProgram(ShaderProgram):
    """
    A simple shader program that is applied across all tiles. Subclasses of this should be constructed to implement
    specific shader effects.
    Usage: TileShaderProgram.get()
    """

    _tile_shader = None

    @classmethod
    def get(cls):
        if cls._tile_shader is None:
            cls._tile_shader = TileShaderProgram()
        return cls._tile_shader

    def __init__(self):
        super().__init__()
        self.current_tile = None
        self.attach_shader(os.path.join(get_resources_directory(), 'shaders', 'tile_vert.glsl'), GL_VERTEX_SHADER)
        self.attach_shader(os.path.join(get_resources_directory(), 'shaders', 'tile_frag.glsl'), GL_FRAGMENT_SHADER)
        self.link_program()

    def pre_render(self, camera):
        if self.current_tile is not None:
            super().pre_render(camera)
            glBindVertexArray(self.current_tile.vertex_array_object)

    def post_render(self, camera):
        if self.current_tile is not None:
            glBindVertexArray(0)
            super().post_render(camera)


class TileMesh(Mesh):
    """ Base tile mesh, contains all VAO/VBO objects """

    def __init__(self, tile: mercantile.Tile, cellsize=30):

        self.grid_size = 256
        vertices = self.grid_size ** 2
        indices = 6 * (self.grid_size - 1) ** 2
        super().__init__(indices, vertices, True, mode=Mesh.TRIANGLES)
        self.mtile = tile
        self.cellsize = cellsize

    def set_buffers(self, vertices, indices, normals, neighbor_meshes):

        row_count = self.grid_size * 3
        total_count = self.grid_size * row_count
        row = [[], [], [], []]
        for i in range(0, row_count, 3):
            row[0].append(math.floor(i + 1))  # top
            row[1].append(math.floor(i / 3 * row_count + 1))  # left
            row[2].append(math.floor(i + 1 + total_count - row_count))  # bottom
            row[3].append(math.floor((i / 3 + 1) * row_count - 2))  # right

        for neighbor in neighbor_meshes:

            if neighbor.mtile.x < self.mtile.x:     # top
                index = 0
            elif neighbor.mtile.x > self.mtile.x:   # bottom
                index = 2
            elif neighbor.mtile.y < self.mtile.y:   # right
                index = 1
            elif neighbor.mtile.y > self.mtile.y:   # left
                index = 2
            else:
                continue    # not a neighbor...

            # Grab neighbor vertices as they exist in OpenGL buffers
            glBindBuffer(GL_ARRAY_BUFFER, neighbor.vertex_buffer)
            neighbor_vertices = map_buffer(GL_ARRAY_BUFFER, numpy.float32, GL_READ_ONLY, vertices.nbytes)
            glUnmapBuffer(GL_ARRAY_BUFFER)
            glBindBuffer(GL_ARRAY_BUFFER, 0)

            indices_to_change = row[index]
            neighbor_indices = row[(index + 2) % 4]
            vertices[indices_to_change] = neighbor_vertices[neighbor_indices]

        # Now allocate everything
        vert_buf = self.acquire_vertex_array()
        vert_buf[:] = vertices.ravel()
        self.release_vertex_array()

        norm_buf = self.acquire_normal_array()
        norm_buf[:] = normals.ravel()
        self.release_normal_array()

        index_buf = self.acquire_index_array()
        index_buf[:] = indices.ravel()
        self.release_index_array()

        self.bounding_box = BoundingBox(0, -10, 0, 256 * self.cellsize, 10, 256 * self.cellsize)


class TileRenderThread(Thread):

    def __init__(self, grid):
        super().__init__()
        self.grid = grid
        self.task = Task("Generating Terrain Mesh")

    def run(self):
        if sys.platform == 'win32':
            asyncio.set_event_loop(asyncio.ProactorEventLoop())
        else:
            asyncio.set_event_loop(asyncio.SelectorEventLoop())

        e = ElevationService()
        e.zoom = self.grid.zoom
        self.task.status = Task.RUNNING
        self.task.description = 'Collecting elevation data...'
        e.get_tiles(self.grid.wgs84, self.task)
        cellsize = self.grid.cellsize
        grid_size = 256

        self.task.description = 'Generating Terrain Mesh'
        self.task.target = len(self.grid.tiles)
        for t in self.grid.tiles:
            data = e.get_grid(t.x, t.y).T

            # Setup vertices
            height, width = data.shape
            indices = numpy.indices(data.shape)
            heightfield = numpy.zeros((height, width, 3), dtype=numpy.float32)
            heightfield[:, :, 0] = indices[0] * cellsize
            heightfield[:, :, 2] = indices[1] * cellsize
            heightfield[:, :, 1] = data

            # Setup indices
            index_array = []
            for i in range(grid_size - 1):
                for j in range(grid_size - 1):
                    a = i + grid_size * j
                    b = i + grid_size * (j + 1)
                    c = (i + 1) + grid_size * (j + 1)
                    d = (i + 1) + grid_size * j
                    index_array += [a, b, d]
                    index_array += [b, c, d]

            # Setup normals
            normals = generate_vertex_normals(
                heightfield.reshape(-1, heightfield.shape[-1]),                             # vertices
                numpy.array([index_array[i:i + 3] for i in range(len(index_array) - 2)])    # faces
            ).reshape(heightfield.shape)

            indices = numpy.array(index_array)
            self.sync_with_main(self.grid.add_tile, (t, heightfield.ravel(), indices.ravel(), normals.ravel()),
                                block=True)
            self.task.inc_progress()

        self.sync_with_main(self.grid.refresh_bounding_box)
        self.grid._can_render = True
        self.sync_with_main(post_redisplay, kwargs={'reset': True})

        self.task.status = Task.COMPLETE
        self.sync_with_main(post_redisplay)


class TileGridRenderable(Renderable):
    """ Rendering interface for a collection of TileMesh's """

    def __init__(self, extent, render=False):
        super().__init__()
        self._extent = extent
        self.zoom = 10
        self.wgs84 = extent.project(Proj(init='EPSG:4326'))
        self.tiles = list(mercantile.tiles(*self.wgs84.as_list(), [self.zoom]))
        self._ul = self.tiles[0]
        self._br = self.tiles[-1]


        self._meshes = []
        self._can_render = False
        self.cellsize = 30

        self.bounding_box = BoundingBox()
        self.shader = TileShaderProgram.get()
        if render:
            TileRenderThread(self).start()

    @property
    def extent(self):
        return self._extent

    @extent.setter
    def extent(self, extent):
        self._extent = extent
        # Todo - reset? Clear house? We should probably look at the tiles that we need and see what needs to be removed

    def add_tile(self, t, vertices, indices, normals):
        tile = TileMesh(t, self.cellsize)

        # resolve seams before allocating buffers
        neighbors = [
            mercantile.Tile(t.x - 1, t.y, t.z),     # left
            mercantile.Tile(t.x, t.y + 1, t.z),     # bottom
            mercantile.Tile(t.x + 1, t.y, t.z),     # right
            mercantile.Tile(t.x, t.y - 1, t.z)      # top
        ]
        neighbor_meshes = [x for x in self._meshes if x.mtile in neighbors]
        tile.set_buffers(vertices, indices, normals, neighbor_meshes)
        self._meshes.append(tile)

    def refresh_bounding_box(self):
        width = (self._br.x - self._ul.x + 1) * 256 * self.cellsize
        height = (self._br.y - self._ul.y + 1) * 256 * self.cellsize

        self.bounding_box = BoundingBox(0, -10, 0, width, 10, height)

    @property
    def mercator_bounds(self):
        ul_bounds = mercantile.xy_bounds(self._ul)
        br_bounds = mercantile.xy_bounds(self._br)
        return mercantile.Bbox(ul_bounds.left, br_bounds.bottom, br_bounds.right, ul_bounds.top)

    @property
    def geographic_bounds(self):
        ul_bounds = mercantile.bounds(self._ul)
        br_bounds = mercantile.bounds(self._br)
        return mercantile.LngLatBbox(ul_bounds.west, br_bounds.south, br_bounds.east, ul_bounds.north)

    def render(self, camera):
        if self._can_render:
            for tile in self._meshes:
                camera.push_matrix()
                camera.matrix *= Matrix44.from_translation(
                    Vector3([(tile.mtile.x - self._ul.x) * 255 * tile.cellsize, 0,
                             (tile.mtile.y - self._ul.y) * 255 * tile.cellsize])
                    )
                self.shader.current_tile = tile
                self.shader.pre_render(camera)
                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, tile.index_buffer)
                glDrawElements(tile.mode, tile.num_indices, GL_UNSIGNED_INT, None)
                self.shader.post_render(camera)
                self.shader.current_tile = None
                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
                camera.pop_matrix()
