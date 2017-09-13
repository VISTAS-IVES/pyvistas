import numpy
from vistas.core.graphics.geometry import Geometry


class BoxLineGeometry(Geometry):
    INDICES = numpy.array([
        0, 1, 2, 3, 0
    ], dtype=numpy.uint8)

    def __init__(self):
        super().__init__(5, 4, mode=Geometry.LINE_STRIP)
        self.indices = self.INDICES


class PolyLineGeometry(Geometry):
    def __init__(self, num_points):
        super().__init__(num_points, num_points, mode=Geometry.LINE_STRIP)
