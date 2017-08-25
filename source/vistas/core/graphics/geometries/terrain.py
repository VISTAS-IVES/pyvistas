from vistas.core.graphics.geometries.plane import PlaneGeometry


class TerrainGeometry(PlaneGeometry):

    def __init__(self, width, height, cellsize, heights=None):
        super().__init__(width, height, cellsize)
        self._heights = None
        if heights:
            self.heights = heights

    @property
    def heights(self):
        return self._heights

    @heights.setter
    def heights(self, heights):
        if heights.shape == (self.width, self.height):
            self._heights = heights
        elif heights.shape == (self.height, self.width):
            self._heights = heights.T
        else:
            raise ValueError("Heights shape does not match z-dimension shape")

        # Now update vertices
        verts = self.vertices.reshape(-1, 3)
        verts[:, :, 2] = heights
        self.vertices = verts

