import os
from typing import List, Optional

from OpenGL.GL import *
import numpy
from pyrr import Vector3

from vistas.core.graphics.mesh import Mesh, MeshShaderProgram
from vistas.core.graphics.renderable import Renderable
from vistas.core.math import Triangle, apply_matrix_44, distance_from
from vistas.core.paths import get_resources_directory
from vistas.core.graphics.raycaster import Ray


# Todo - maybe we should implement a quadtree (or oct-tree) for large terrains?


class MeshRenderable(Renderable):
    """ Base mesh renderable class, combining a Mesh and a MeshShaderProgram into an OpenGL-renderable object. """

    def __init__(self, mesh=None):
        super().__init__()

        self._mesh = None
        self.textures_map = {}
        self.mesh = Mesh() if mesh is None else mesh

    def __del__(self):
        self._mesh = None

    @property
    def mesh(self):
        return self._mesh

    @mesh.setter
    def mesh(self, mesh):
        self._mesh = mesh
        self.bounding_box = mesh.bounding_box
        self.textures_map = {}

    def render(self, camera):
        if self.mesh.has_index_array and self.mesh.has_vertex_array:
            for texture in self.textures_map.values():
                texture.pre_render(1, camera)

            self.mesh.shader.pre_render(camera)

            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.mesh.index_buffer)
            glDrawElements(self.mesh.mode, self.mesh.num_indices, GL_UNSIGNED_INT, None)

            self.mesh.shader.post_render(camera)

            for texture in self.textures_map.values():
                texture.post_render(1, camera)

            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

    @property
    def selection_shader(self):
        shader = MeshShaderProgram(self.mesh)
        shader.attach_shader(os.path.join(
            get_resources_directory(), 'shaders', 'mesh_render_for_selection_hit_vert.glsl'
        ), GL_VERTEX_SHADER)
        shader.attach_shader(os.path.join(
            get_resources_directory(), 'shaders', 'mesh_render_for_selection_hit_frag.glsl'
        ), GL_FRAGMENT_SHADER)
        return shader

    def render_for_selection_hit(self, camera, r, g, b):
        if self.mesh is None:
            return

        shader = self.selection_shader
        shader.pre_render(camera)
        glUniform4f(shader.get_uniform_location('color'), r, g, b, 1.0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.mesh.index_buffer)

        glDrawElements(self.mesh.mode, self.mesh.num_indices, GL_UNSIGNED_INT, None)

        shader.post_render(camera)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

    def aqcuire_texture(self, texture):
        self.textures_map[texture.number] = texture

    def release_texture(self, number):
        return self.textures_map.pop(number)

    def raycast(self, raycaster) -> List[Renderable.Intersection]:
        intersects = []
        if self.bounding_box is None or not raycaster.ray.intersects_bbox(self.bounding_box) or self.mesh.shader is None:
            return intersects

        pos = self.mesh.vertices.reshape(-1, 3)
        indices = self.mesh.indices.reshape(-1, 3)
        uvs = self.mesh.texcoords
        v1, v2, v3 = numpy.rollaxis(pos[indices], axis=-2)

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
            intersection = Renderable.Intersection(distance, point, self)
            va, vb, vc = Vector3(v1[a]), Vector3(v2[b]), Vector3(v3[c])
            if uvs is not None:
                uv_a = Vector3([*uvs[a * 2: a * 2 + 2], 0])
                uv_b = Vector3([*uvs[b * 2: b * 2 + 2], 0])
                uv_c = Vector3([*uvs[c * 2: c * 2 + 2], 0])
                intersection.uv = uv_intersection(point, va, vb, vc, uv_a, uv_b, uv_c)
            intersection.face = Renderable.Face(a, b, c, Triangle(vc, vb, va).normal)
            intersects.append(intersection)
        return intersects
