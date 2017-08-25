from numpy import indices, zeros, float32, array
from pyrr.vector3 import generate_vertex_normals

from vistas.core.graphics.geometry import Geometry


class PlaneGeometry(Geometry):
    """ A flat plane geometry with normals and  """

    def __init__(self, width, height, cellsize):
        num_vertices = width * height
        num_indices = 6 * (width - 1) * (height - 1)
        super().__init__(num_indices=num_indices, num_vertices=num_vertices, has_normal_array=True,
                         has_texture_coords=True, mode=Geometry.TRIANGLES)

        self.cellsize = cellsize
        self.width = width
        self.height = height

        vertices = zeros((height, width, 3), dtype=float32)
        i = indices((height, width))
        vertices[:, :, 0] = i[0] * cellsize
        vertices[:, :, 1] = i[1] * cellsize

        index_array = []
        for j in range(height - 1):
            for i in range(width - 1):
                a = i + width * j
                b = i + width * (j + 1)
                c = (i + 1) + width * (j + 1)
                d = (i + 1) + width * j
                index_array += [a, b, d]
                index_array += [b, c, d]
        index_array = array(index_array)

        normals = generate_vertex_normals(vertices.reshape(-1, 3), index_array.reshape(-1, 3))

        tex_coords = zeros((height, width, 2))
        tex_coords[:, :, 0] = i[0] / height     # u
        tex_coords[:, :, 1] = 1 - i[1] / width  # v

        self.vertices = vertices
        self.indices = index_array
        self.normals = normals
        self.texcoords = tex_coords
