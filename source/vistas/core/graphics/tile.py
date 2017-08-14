import math
import os

import mercantile
import numpy
from OpenGL.GL import *
from pyproj import Proj
from pyrr import Vector3, Matrix44
from pyrr.vector3 import generate_vertex_normals

from vistas.core.gis.elevation import ElevationService, meters_per_px, TILE_SIZE
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

    def __init__(self):
        super().__init__()
        self.current_tile = None
        self.attach_shader(os.path.join(get_resources_directory(), 'shaders', 'tile_vert.glsl'), GL_VERTEX_SHADER)
        self.attach_shader(os.path.join(get_resources_directory(), 'shaders', 'tile_frag.glsl'), GL_FRAGMENT_SHADER)
        self.link_program()

        self.height_multiplier = 1.0

    def pre_render(self, camera):
        if self.current_tile is not None:
            super().pre_render(camera)
            self.uniform1f('heightMultiplier', self.height_multiplier)
            glBindVertexArray(self.current_tile.vertex_array_object)

    def post_render(self, camera):
        if self.current_tile is not None:
            glBindVertexArray(0)
            super().post_render(camera)


class TileMesh(Mesh):
    """ Base tile mesh, contains all VAO/VBO objects """

    def __init__(self, tile: mercantile.Tile, meters_per_px):
        vertices = TILE_SIZE ** 2
        indices = 6 * (TILE_SIZE - 1) ** 2
        super().__init__(indices, vertices, True, mode=Mesh.TRIANGLES)
        self.mtile = tile
        self.meters_per_px = meters_per_px

    def set_buffers(self, vertices, indices, normals, neighbor_meshes):

        row_count = TILE_SIZE * 3
        total_count = TILE_SIZE * row_count
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

        self.bounding_box = BoundingBox(0, float(vertices.min()) / self.meters_per_px, 0, TILE_SIZE,
                                        float(vertices.max()) / self.meters_per_px, TILE_SIZE)


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

        self.sync_with_main(self.grid.refresh_bounding_box)
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

        self.zoom = zoom    # Update things appropriately

        self.bounding_box = BoundingBox()
        self.shader = TileShaderProgram()
        TileRenderThread(self).start()

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
        for tile in self._meshes:
            camera.push_matrix()
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
