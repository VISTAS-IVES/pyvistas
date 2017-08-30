from numpy import ones

from vistas.core.graphics.geometry import Geometry


class FeatureGeometry(Geometry):

    def __init__(self, num_indices, num_vertices, indices=None,  vertices=None):
        super().__init__(
            num_indices, num_vertices, has_normal_array=True, has_color_array=True, mode=Geometry.TRIANGLES
        )
        if indices is not None and self.vertices is not None:
            self.indices = indices
            self.vertices = vertices
            self.compute_bounding_box()
        self.colors = ones(num_vertices * 3, float) * 0.5  # init the color buffer with grey
