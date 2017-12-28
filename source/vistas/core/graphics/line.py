import numpy

from vistas.core.graphics.geometry import Geometry


class BoxLineGeometry(Geometry):
    INDICES = numpy.array([
        0, 1, 2, 3, 0
    ], dtype=numpy.uint8)

    def __init__(self, vertices=None):
        super().__init__(5, 4, mode=Geometry.LINE_STRIP)
        self.indices = self.INDICES
        if vertices is not None:
            self.vertices = vertices
            self.compute_bounding_box()


class PolygonLineGeometry(Geometry):
    def __init__(self, num_points, vertices=None):
        super().__init__(num_points, num_points, mode=Geometry.LINE_STRIP)
        if vertices is not None:
            self.indices = numpy.arange(num_points, dtype=numpy.uint8)
            self.vertices = vertices
            self.compute_bounding_box()
