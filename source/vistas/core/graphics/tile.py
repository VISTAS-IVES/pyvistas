import os

import numpy
import mercantile
from OpenGL.GL import *
from pyrr.vector3 import generate_normals

from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.mesh import Mesh
from vistas.core.graphics.renderable import Renderable
from vistas.core.graphics.shader import ShaderProgram
from vistas.core.paths import get_resources_directory


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
        indices = 131068    # (256-1) * 256 * 2 + ((256 - 1) * 2 - 2), which is the number of indices
        vertices = 256**2
        super().__init__(indices, vertices, True)
        self.mtile = tile
        self.shader = TileShaderProgram.get()
        self.cellsize = cellsize

    def set_tile_data(self, data, xpos, zpos):

        # Setup vertices
        height, width = data.shape
        indices = numpy.indices(data.shape)
        heightfield = numpy.zeros((height, width, 3))
        heightfield[:, :, 0] = indices[0] * self.cellsize
        heightfield[:, :, 2] = indices[1] * self.cellsize
        heightfield[:, :, 1] = data

        self.bounding_box = BoundingBox(0, -10, 0, 256 * self.cellsize, 10, 256 * self.cellsize)

        # Setup indices
        index_array = []
        for i in range(height - 1):
            if i > 0:
                index_array.append(i * width)
            for j in range(width):
                index_array.append(i * width + j)
                index_array.append((i + 1) * width + j)
            if i < height - 2:
                index_array.append((i + 1) * width + (width - 1))

        # Setup normals
        verts = heightfield.reshape(-1, heightfield.shape[-1])
        faces = numpy.array([index_array[i:i + 3] for i in range(len(index_array) - 2)])
        norm = numpy.zeros(verts.shape, dtype=verts.dtype)
        tris = verts[faces]
        n = generate_normals(tris[::, 2], tris[::, 0], tris[::, 1])
        norm[faces[:, 0]] += n
        norm[faces[:, 1]] += n
        norm[faces[:, 2]] += n
        normals = norm.reshape(heightfield.shape)

        # Now allocate everything
        vert_buf = self.acquire_vertex_array()
        vert_buf[:] = heightfield.ravel()
        self.release_vertex_array()

        norm_buf = self.acquire_normal_array()
        norm_buf[:] = normals.ravel()
        self.release_normal_array()

        index_buf = self.acquire_index_array()
        index_buf[:] = index_array
        self.release_index_array()


class TileRenderable(Renderable):
    """ Rendering interface for Tiles. """

    def __init__(self, cellsize=30):
        super().__init__()
        self.tile = TileMesh(cellsize)
        self.bounding_box = self.tile.bounding_box

    def render(self, camera):
        self.tile.shader.current_tile = self.tile
        self.tile.shader.pre_render(camera)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.tile.index_buffer)
        glDrawElements(self.tile.mode, self.tile.num_indices, GL_UNSIGNED_INT, None)

        self.tile.shader.post_render(camera)
        self.tile.shader.current_tile = None

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)


class TileGridRenderable(Renderable):
    """ Rendering interface for a group of TileMesh's """

    def __init__(self):
        super().__init__()
        self._tiles = []
        self.bounding_box = None
        self.shader = TileShaderProgram.get()

    @property
    def tiles(self):
        return self._tiles

    @tiles.setter
    def tiles(self, tiles):
        self._tiles = tiles
        self._resolve_seams()
        self.refresh_bounding_box()

    def add_tile(self, tile):
        self._tiles.append(tile)

    def _resolve_seams(self):
        """ Resolves seems to eliminate weird looking edges """

        pass

    def refresh_bounding_box(self):
        bbox = self.tiles[0].bounding_box
        for obj in self.tiles[1:]:
            bbox.min_x = min(obj.bounds.min_x, bbox.min_x)
            bbox.max_x = max(obj.bounds.max_x, bbox.max_x)
            bbox.min_y = min(obj.bounds.min_y, bbox.min_y)
            bbox.max_y = max(obj.bounds.max_y, bbox.max_y)
            bbox.min_z = min(obj.bounds.min_z, bbox.min_z)
            bbox.max_z = max(obj.bounds.max_z, bbox.max_z)
        self.bounding_box = bbox

    def render(self, camera):
        for tile in self._tiles:
            self.shader.current_tile = tile
            self.shader.pre_render(camera)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, tile.index_buffer)
            glDrawElements(tile.mode, tile.num_indices, GL_UNSIGNED_INT, None)
            self.shader.post_render(camera)
            self.shader.current_tile = None
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
