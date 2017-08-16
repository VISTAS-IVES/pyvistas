import os
from typing import List, Optional

from OpenGL.GL import *
from numpy import floor
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

    def raycast(self, raycaster, camera) -> List[Renderable.Intersection]:
        import time
        intersects = []
        t = time.time()
        if self.bounding_box is None or not raycaster.ray.intersects_bbox(self.bounding_box) or self.mesh.shader is None:
            return intersects
        print('Time to bbox intersect: {}'.format(time.time() - t))
        t = time.time()
        # ray intersects this object, now check for face intersections
        position = self.mesh.vertices

        if self.mesh.has_texture_coords:
            uv = self.mesh.texcoords
        else:
            uv = None

        if self.mesh.has_index_array:
            index = self.mesh.indices
        else:
            index = None

        va = Vector3()
        vb = Vector3()
        vc = Vector3()
        uv_a = Vector3()
        uv_b = Vector3()
        uv_c = Vector3()

        def uv_intersection(point, p1, p2, p3, uv1, uv2, uv3):
            barycoord = Triangle(p1, p2, p3).barycoord_from_pos(point)
            uv1 *= barycoord.x
            uv2 *= barycoord.y
            uv3 *= barycoord.z
            return uv1 + uv2 + uv3

        def check_intersection(a, b, c) -> Optional[Renderable.Intersection]:
            intersect = raycaster.ray.it(c, b, a)
            if intersect is not None:
                distance = distance_from(raycaster.ray.origin, intersect)
                return Renderable.Intersection(distance, intersect, self)
            else:
                return None

        def check_buffer_intersection(a, b, c) -> Optional[Renderable.Intersection]:
            nonlocal va, vb, vc, uv_a, uv_b, uv_c
            va = Vector3(position[a * 3: a * 3 + 3])
            vb = Vector3(position[b * 3: b * 3 + 3])
            vc = Vector3(position[c * 3: c * 3 + 3])
            intersection = check_intersection(va, vb, vc)
            if intersection is not None:

                # Obtain the uv coordinates for this triangle
                if uv is not None:
                    uv_a = Vector3([*uv[a * 2: a * 2 + 2], 0])
                    uv_b = Vector3([*uv[b * 2: b * 2 + 2], 0])
                    uv_c = Vector3([*uv[c * 2: c * 2 + 2], 0])
                    intersection.uv = uv_intersection(intersection.point, va, vb, vc, uv_a, uv_b, uv_c)

                # Add the intersection's face information
                intersection.face = Renderable.Face(a, b, c, Triangle(vc, vb, va).normal)
            return intersection

        if index is not None:
            for i in range(0, self.mesh.num_indices, 3):
                a = index[i]
                b = index[i + 1]
                c = index[i + 2]
                intersection = check_buffer_intersection(a, b, c)
                if intersection is not None:
                    intersection.face_index = floor(i / 3)
                    intersects.append(intersection)
        print("Elapsed time: {}".format(time.time() - t))
        return intersects
