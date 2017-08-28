import numpy
from OpenGL.GL import *

from vistas.core.graphics.geometry import InstancedGeometry


class VectorGeometry(InstancedGeometry):
    """
    An InstancedGeometry for rendering large amounts of vectors efficiently.
                                  /|
                                 / |
                                /  |_______________
                                \  |_______________|
                                 \ |
                                  \|
    VectorGeometry requires that the instanced data be 7 floats wide per instance. Specification of how the floats are
    aranged in the array are as follows:

    0-2: Position of the vector in model-space (i.e. before a Camera's matrix is applied).
    3:   Direction of the vector in polar degrees.
    4:   Tilt of the vector relative to the xy plane.
    5:   Magnitude of the vector relative to the size of the other vectors.
    6:   Value data, such as a visibility flag.
    """

    VERTICES = numpy.array([
        -.1, 0, 1,      # arrow shaft
        -.1, 0, -0.2,
        .1, 0, 1,
        .1, 0, -0.2,
        -0.3, 0.0, 0.1,  # arrow head
        0.0, 0.3, 0.1,
        0.3, 0.0, 0.1,
        0.0, -0.3, 0.1,
        0.0, 0.0, -0.5  # tip
    ], dtype=GLfloat)

    INDICES = numpy.array([
        0, 1, 2,    # arrow shaft
        1, 2, 3,
        4, 5, 6,    # arrow head base,
        4, 7, 6,
        4, 5, 8,    # head
        5, 6, 8,
        6, 7, 8,
        7, 4, 8,
    ], dtype=GLushort)

    BUFFER_WIDTH = 7
    BUFFER_SPEC = [3, 1, 1, 1, 1]   # position, direction, tile, magnitude, value

    def __init__(self, max_instances=0, data=None):
        super().__init__(
            num_indices=self.INDICES.size, num_vertices=self.VERTICES.size // 3, mode=GL_TRIANGLES,
            max_instances=max_instances, instance_buffer_spec=self.BUFFER_SPEC
        )
        self.indices = self.INDICES.copy()
        self.vertices = self.VERTICES.copy()
        self.compute_bounding_box()
        if data is not None:
            self.vector_data = data

    @property
    def vector_data(self):
        return self.instance_data

    @vector_data.setter
    def vector_data(self, data):
        data_size = data.nbytes // sizeof(GLfloat)
        assert data_size % self.BUFFER_WIDTH == 0
        self.instance_data = data
        self.num_instances = data_size // self.BUFFER_WIDTH
