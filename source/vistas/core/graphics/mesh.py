import numpy
from OpenGL.GL import *
from pyrr import Matrix44, Vector3

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
        if self.bounding_box is None or not raycaster.ray.intersects_bbox(self.bounding_box_world) \
                or self.shader is None:
            self.selected = False
            return intersects

        vertices = numpy.copy(self.geometry.vertices.reshape(-1, 3))
        indices = self.geometry.indices.reshape(-1, 3)
        uvs = self.geometry.texcoords

        # Translate copied vertices to world coordinates
        vertices[:, 0] += self.position.x
        vertices[:, 1] += self.position.y
        vertices[:, 2] += self.position.z
        v1, v2, v3 = numpy.rollaxis(vertices[indices], axis=-2)

        def uv_intersection(point, p1, p2, p3, uv1, uv2, uv3):
            barycoord = Triangle(p1, p2, p3).barycoord_from_pos(point)
            uv1 *= barycoord.x
            uv2 *= barycoord.y
            uv3 *= barycoord.z
            return uv1 + uv2 + uv3

        distances, face_indices = raycaster.ray.intersect_triangles(v3, v2, v1)
        for i, d in enumerate(distances):
            point = raycaster.ray.at(d)
            distance = distance_from(raycaster.ray.origin, point)
            face = indices[face_indices[i]]
            a, b, c = face
            intersection = Intersection(distance, point, self)
            if indices.size == vertices.shape[0]:                   # Handle when vertices are all unique
                va, vb, vc = [Vector3(v) for v in vertices[face]]
            else:
                va, vb, vc = Vector3(v1[a]), Vector3(v2[b]), Vector3(v3[c])
            if uvs is not None:
                uv_a = Vector3([*uvs[a * 2: a * 2 + 2], 0])
                uv_b = Vector3([*uvs[b * 2: b * 2 + 2], 0])
                uv_c = Vector3([*uvs[c * 2: c * 2 + 2], 0])
                intersection.uv = uv_intersection(point, va, vb, vc, uv_a, uv_b, uv_c)
            intersection.face = Face(a, b, c, Triangle(vc, vb, va).normal)
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
