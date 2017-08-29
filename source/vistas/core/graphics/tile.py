import math
import os

import mercantile
import numpy
from OpenGL.GL import *
from pyproj import Proj
from pyrr import Vector3, Matrix44
from pyrr.vector3 import generate_vertex_normals

from vistas.core.bounds import BoundingBox
from vistas.core.gis.elevation import ElevationService, meters_per_px, TILE_SIZE
from vistas.core.graphics.mesh import Mesh
from vistas.core.graphics.shader import ShaderProgram
from vistas.core.graphics.utils import map_buffer
from vistas.core.paths import get_resources_directory
from vistas.core.task import Task
from vistas.core.threading import Thread
from vistas.ui.utils import post_redisplay



class TileRenderThread(Thread):

    def __init__(self, grid):
        super().__init__()
        self.grid = grid
        self.task = Task("Generating Terrain Mesh")

    def run(self):

        self.init_event_loop()

        e = ElevationService()
        e.zoom = self.grid.zoom
        self.task.status = Task.RUNNING
        self.task.description = 'Collecting Elevation Data'
        e.get_tiles(self.grid.wgs84, self.task)

        self.task.description = 'Generating Terrain Mesh'
        self.task.target = len(self.grid.tiles)
        grids = e.create_data_dem(self.grid.extent, self.grid.zoom)

        for t in self.grid.tiles:
            data = grids[t].T

            # Elevation tiles are assumed to be 256 across. Match the tile grid to the appropriate size we want
            height, width = data.shape

            if height != TILE_SIZE or width != TILE_SIZE:
                # Time to sample down

                h_stride = height // TILE_SIZE
                w_stride = width // TILE_SIZE
                data = data[::h_stride, ::w_stride]

            # Setup vertices
            height, width = data.shape
            indices = numpy.indices(data.shape)
            heightfield = numpy.zeros((height, width, 3), dtype=numpy.float32)
            heightfield[:, :, 0] = indices[0]
            heightfield[:, :, 2] = indices[1]
            heightfield[:, :, 1] = data / self.grid.meters_per_px

            # Setup indices
            index_array = []
            for i in range(TILE_SIZE - 1):
                for j in range(TILE_SIZE - 1):
                    a = i + TILE_SIZE * j
                    b = i + TILE_SIZE * (j + 1)
                    c = (i + 1) + TILE_SIZE * (j + 1)
                    d = (i + 1) + TILE_SIZE * j
                    index_array += [a, b, d]
                    index_array += [b, c, d]

            indices = numpy.array(index_array)

            # Setup normals
            normals = generate_vertex_normals(
                heightfield.reshape(-1, 3),                     # vertices
                indices.reshape(-1, 3)         # faces
            ).reshape(heightfield.shape)
            self.sync_with_main(self.grid.add_tile, (t, heightfield.ravel(), indices.ravel(), normals.ravel()),
                                block=True)
            self.task.inc_progress()

        self.task.status = Task.COMPLETE
        self.sync_with_main(post_redisplay)


class TileLayerRenderable(Renderable):
    """ Rendering interface for a collection of TileMesh's """

    def __init__(self, extent, zoom=10):
        super().__init__()
        self.extent = extent
        self.wgs84 = extent.project(Proj(init='EPSG:4326'))
        self.tiles = []
        self._ul = None
        self._br = None
        self._zoom = None
        self._meshes = []
        self.meters_per_px = None
        self.bounding_box = BoundingBox()
        self.shader = TileShaderProgram()
        self.zoom = zoom  # Update things appropriately

    @property
    def height_multiplier(self):
        return self.shader.height_multiplier

    @height_multiplier.setter
    def height_multiplier(self, height_multiplier):
        self.shader.height_multiplier = height_multiplier

    @property
    def zoom(self):
        return self._zoom

    @zoom.setter
    def zoom(self, zoom):
        if zoom != self._zoom:
            self._zoom = zoom
            self.tiles = list(mercantile.tiles(*self.wgs84.as_list(), [self.zoom]))
            self._ul = self.tiles[0]
            self._br = self.tiles[-1]
            self.refresh_bounding_box()
            self.meters_per_px = meters_per_px(self.zoom)

            del self._meshes[:]
            TileRenderThread(self).start()

    def add_tile(self, t, vertices, indices, normals):
        tile = TileMesh(t, self.meters_per_px)

        # Determine neighbors for this tile
        neighbors = [
            mercantile.Tile(t.x - 1, t.y, t.z),     # left
            mercantile.Tile(t.x, t.y + 1, t.z),     # bottom
            mercantile.Tile(t.x + 1, t.y, t.z),     # right
            mercantile.Tile(t.x, t.y - 1, t.z)      # top
        ]
        neighbor_meshes = [x for x in self._meshes if x.mtile in neighbors]

        # Allocate OpenGL buffers
        tile.set_buffers(vertices, indices, normals, neighbor_meshes)
        self._meshes.append(tile)

    def refresh_bounding_box(self):
        width = (self._br.x - self._ul.x + 1) * TILE_SIZE
        height = (self._br.y - self._ul.y + 1) * TILE_SIZE
        self.bounding_box = BoundingBox(0, 0, -10, width, height, 10)

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

    def raycast(self, raycaster):
        return []

    def render(self, camera):
        for tile in self._meshes:
            camera.push_matrix()

            # Move from y-up to z-up
            camera.matrix *= Matrix44.from_translation(
                Vector3([(self._br.x - self._ul.x + 1) * TILE_SIZE, 0, 0])
            )
            camera.matrix *= Matrix44.from_x_rotation(numpy.pi / 2)
            camera.matrix *= Matrix44.from_z_rotation(numpy.pi)
            camera.matrix *= Matrix44.from_translation(
                Vector3([(tile.mtile.x - self._ul.x) * (TILE_SIZE - 1), 0,
                         (tile.mtile.y - self._ul.y) * (TILE_SIZE - 1)])
                )
            self.shader.current_tile = tile
            self.shader.pre_render(camera)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, tile.index_buffer)
            glDrawElements(tile.mode, tile.num_indices, GL_UNSIGNED_INT, None)
            self.shader.post_render(camera)
            self.shader.current_tile = None
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
            camera.pop_matrix()
