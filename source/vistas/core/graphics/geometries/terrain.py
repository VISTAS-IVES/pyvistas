import mercantile
from vistas.core.gis.elevation import meters_per_px, TILE_SIZE
from OpenGL.GL import *
from vistas.core.graphics.geometries.plane import PlaneGeometry
from vistas.core.graphics.utils import map_buffer


class TerrainGeometry(PlaneGeometry):
    """ Basic terrain-like geometry with height represented in the z-dimension. """

    def __init__(self, width, height, cellsize, heights=None):
        super().__init__(width, height, cellsize)
        self._heights = None
        if heights is not None:
            self.heights = heights

    @property
    def heights(self):
        return self._heights

    @heights.setter
    def heights(self, heights):
        """ A 2D array of terrain heights, usually created from source data. """

        assert heights.shape == (self.height, self.width)
        self._heights = heights
        verts = self.vertices.reshape((self.height, self.width, 3))
        verts[:, :, 2] = heights
        self.vertices = verts
        self.compute_bounding_box()
        self.compute_normals()


class TerrainColorGeometry(TerrainGeometry):
    """ A TerrainGeometry with a float-wide vertex buffer for data. """

    def __init__(self, width, height, cellsize, heights=None, values=None, value_size=1):
        super().__init__(width, height, cellsize, heights)

        self._values = None
        self.value_size = value_size

        # Add a 'value' vertex buffer
        self.value_buffer = glGenBuffers(1)
        glBindVertexArray(self.vertex_array_object)
        glBindBuffer(GL_ARRAY_BUFFER, self.value_buffer)
        glBufferData(GL_ARRAY_BUFFER, self.num_vertices * value_size * sizeof(GLfloat), None, GL_DYNAMIC_DRAW)

        # Override location 3 to be 'value', since we are not using the 'color' array available from Geometry
        glEnableVertexAttribArray(3)    # location 3 = 'value'
        glVertexAttribPointer(3, self.value_size, GL_FLOAT, GL_FALSE, sizeof(GLfloat), None)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

        if values is not None:
            self.values = values

    def acquire_value_array(self, access=GL_WRITE_ONLY):
        glBindBuffer(GL_ARRAY_BUFFER, self.value_buffer)
        return map_buffer(GL_ARRAY_BUFFER, GLfloat, access, self.num_vertices * self.value_size * sizeof(GLfloat))

    def release_value_array(self):
        glUnmapBuffer(GL_ARRAY_BUFFER)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    @property
    def values(self):
        if self._values is None:
            values_buf = self.acquire_value_array(GL_READ_ONLY)
            self._values = values_buf[:]
            self.release_value_array()
        return self._values

    @values.setter
    def values(self, values):
        assert values.shape == (self.height, self.width)
        self._values = values.ravel()
        values_buf = self.acquire_value_array()
        values_buf[:] = self._values
        self.release_value_array()


class TerrainTileGeometry(TerrainGeometry):
    """ TerrainGeometry that is derived from XYZ tiles. """

    def __init__(self, tile: mercantile.Tile, heights=None):
        super().__init__(TILE_SIZE, TILE_SIZE, 1, heights=heights)
        self.mtile = tile

    @property
    def zoom(self):
        return self.mtile.z

    @TerrainGeometry.heights.setter
    def heights(self, heights):
        assert heights.shape == (TILE_SIZE, TILE_SIZE)
        self._heights = heights / meters_per_px(self.zoom)
        verts = self.vertices.reshape((self.height, self.width, 3))
        verts[:, :, 2] = heights
        self.vertices = verts
        self.compute_bounding_box()
        self.compute_normals()
