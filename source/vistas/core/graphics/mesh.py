import numpy
from OpenGL.GL import *
from pyrr import Matrix44, Vector3

from vistas.core.bounds import BoundingBox
from vistas.core.color import RGBColor
from vistas.core.graphics.bounding_box import BoundingBoxHelper
from vistas.core.graphics.geometry import Geometry, InstancedGeometry
from vistas.core.graphics.object import Object3D, Face, Intersection
from vistas.core.math import Triangle, distance_from
from vistas.core.plugins.visualization import VisualizationPlugin3D


class Mesh(Object3D):
    """ A customizable object containing a Geometry and a ShaderProgram for rendering custom effects. """

    def __init__(self, geometry, shader, plugin=None):
        """
        Constructor
        :param geometry: The Geometry to use when drawing this Mesh.
        :param shader: The ShaderProgram to use for rendering effects onto this Mesh's Geometry.
        :param plugin: The visualization plugin associated with this Mesh.
        """
        super().__init__()

        self.geometry = geometry
        self.shader = shader
        self.selected = False

        if plugin:
            # Meshes can only be associated with a 3D viz plugin
            assert isinstance(plugin, VisualizationPlugin3D)

        self.plugin = plugin
        self.bbox_helper = BoundingBoxHelper(self)
        self.visible = True
        self.update()

    @property
    def bounding_box(self):
        return self.geometry.bounding_box

    def update(self):
        self.bbox_helper.update()

    def raycast(self, raycaster):
        intersects = []
        ray = raycaster.ray
        if self.bounding_box is None or not ray.intersects_bbox(self.bounding_box_world) \
                or self.shader is None:
            self.selected = False
            return intersects

        vertices = numpy.copy(self.geometry.vertices.reshape(-1, 3))
        indices = self.geometry.indices.reshape(-1, 3)

        # Translate copied vertices to world coordinates
        vertices[:, 0] += self.position.x
        vertices[:, 1] += self.position.y
        vertices[:, 2] += self.position.z

        top = BoundingBox(
            self.bounding_box_world.min_x,
            self.bounding_box_world.min_y,
            self.bounding_box_world.min_z,
            self.bounding_box_world.max_x,
            self.bounding_box_world.max_y,
            self.bounding_box_world.max_z,
        )

        bottom = BoundingBox(
            top.min_x,
            top.min_y,
            top.min_z,
            top.max_x,
            top.max_y,
            top.min_z
        )

        # Translate z for shaders that implement height_factor
        height_factor = getattr(self.shader, 'height_factor', None)
        if height_factor:
            vertices[:, 2] *= height_factor
            top.max_z *= height_factor

        top = ray.intersect_bbox(top)
        bottom = ray.intersect_bbox(bottom)
        cellsize = getattr(self.geometry, 'cellsize', None)

        # Attempt to minimize the number of vertices we test against.
        if all(x is not None for x in (top, bottom)) and cellsize is not None:

            # Determine the smallest grid from the bbox ray intersections to minimize the triangle calculation
            min_x = min(top.x, bottom.x)
            min_y = min(top.y, bottom.y)
            max_x = max(top.x, bottom.x)
            max_y = max(top.y, bottom.y)
            width = getattr(self.geometry, 'width')
            height = getattr(self.geometry, 'height')
            verts = vertices.reshape((height, width, 3))

            # Grid indices
            min_x = int(min_x // cellsize)
            min_y = int(min_y // cellsize)
            max_x = int(max_x // cellsize)
            max_y = int(max_y // cellsize)
            if min_x == max_x:              # Must be at least 1x1 grid
                max_x += 1
            if min_y == max_y:
                max_y += 1

            grid = verts[min_x:max_x+1, min_y:max_y+1]
            height, width, _ = grid.shape
            grid = grid.reshape(-1, 3)

            index_array = []
            for j in range(height - 1):
                for i in range(width - 1):
                    a = i + width * j
                    b = i + width * (j + 1)
                    c = (i + 1) + width * (j + 1)
                    d = (i + 1) + width * j
                    index_array += [a, b, d]
                    index_array += [b, c, d]

            if not index_array:
                return intersects

            index_array = numpy.array(index_array).reshape(-1, 3)
            v1, v2, v3 = numpy.rollaxis(grid[index_array], axis=-2)

        # Otherwise, use all triangles
        else:
            v1, v2, v3 = numpy.rollaxis(vertices[indices], axis=-2)

        # Compute triangle intersections and return hits
        distances, face_indices = raycaster.ray.intersect_triangles(v3, v2, v1)
        for i, d in enumerate(distances):
            point = raycaster.ray.at(d)
            distance = distance_from(raycaster.ray.origin, point)
            intersection = Intersection(distance, point, self)
            intersects.append(intersection)

        self.selected = len(intersects) > 0
        return intersects

    def render_bounding_box(self, color, camera):
        if self.selected:
            self.bbox_helper.render(color, camera)
        else:
            self.bbox_helper.render(RGBColor(1.0, 1.0, 0.0), camera)

    def render(self, camera):
        if self.geometry.has_index_array and self.geometry.has_vertex_array and self.visible:

            camera.push_matrix()
            camera.matrix *= Matrix44.from_translation(self.position)

            self.shader.pre_render(camera)
            glBindVertexArray(self.geometry.vertex_array_object)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.geometry.index_buffer)

            # Which kind of Geometry do we have?
            if isinstance(self.geometry, InstancedGeometry):
                self.shader.uniform3fv("vertexScalars", 1, numpy.array(self.geometry.vertex_scalars))
                self.shader.uniform3fv("vertexOffsets", 1, numpy.array(self.geometry.vertex_offsets))
                if self.geometry.num_instances:
                    glDrawElementsInstanced(
                        self.geometry.mode, self.geometry.num_indices, GL_UNSIGNED_INT, None, self.geometry.num_instances
                    )
            elif isinstance(self.geometry, Geometry):
                glDrawElements(self.geometry.mode, self.geometry.num_indices, GL_UNSIGNED_INT, None)

            glBindVertexArray(0)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
            camera.pop_matrix()
            self.shader.post_render(camera)
