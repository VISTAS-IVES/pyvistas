from typing import Optional, List

import numpy
from pyrr import Vector3

from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.renderable import Renderable


class Ray:
    """
    Representation of a ray in 3D space. Rays emit from an origin along a direction.
    https://github.com/mrdoob/three.js/blob/master/src/math/Ray.js
    """

    def __init__(self, origin: Optional[Vector3]=None, direction: Optional[Vector3]=None):
        self.origin = origin if origin is not None else Vector3()
        self.direction = direction if direction is not None else Vector3()
        self.direction.normalize()

    def at(self, t):
        """ The distance along the Ray to retrieve a position for. """

        return self.direction * t + self.origin

    def intersects_bbox(self, bbox: BoundingBox):
        return self.intersect_bbox(bbox) is not None

    def intersect_bbox(self, bbox: BoundingBox):
        invdirx, invdiry, invdirz = 1 / self.direction  # Any or all could evaluate to numpy.inf, handled below

        if invdirx >= 0:
            tmin = (bbox.min_x - self.origin.x) * invdirx
            tmax = (bbox.max_x - self.origin.x) * invdirx
        else:
            tmin = (bbox.max_x - self.origin.x) * invdirx
            tmax = (bbox.min_x - self.origin.x) * invdirx

        if invdiry >= 0:
            tymin = (bbox.min_y - self.origin.y) * invdiry
            tymax = (bbox.max_y - self.origin.y) * invdiry
        else:
            tymin = (bbox.max_y - self.origin.y) * invdiry
            tymax = (bbox.min_y - self.origin.y) * invdiry

        if tmin > tymax or tymin > tmax:
            return None

        # These lines handle when t_min or t_max are numpy.nan or numpy.inf
        if tymin > tmin or tmin != tmin:
            tmin = tymin

        if tymax < tmax or tmax != tmax:
            tmax = tymax

        if invdirz >= 0:
            tzmin = (bbox.min_z - self.origin.z) * invdirz
            tzmax = (bbox.max_z - self.origin.z) * invdirz
        else:
            tzmin = (bbox.max_z - self.origin.z) * invdirz
            tzmax = (bbox.min_z - self.origin.z) * invdirz

        if tmin > tzmax or tzmin > tmax:
            return None

        if tzmin > tmin or tmin != tmin:
            tmin = tzmin

        if tzmax < tmax or tmax != tmax:
            tmax = tzmax

        # Return point closest to the ray on the positive side
        if tmax < 0:
            return None

        return self.at(tmin if tmin >= 0 else tmax)

    def it(self, a, b, c):
        e1 = b - a
        e2 = c - a
        pvec = self.direction.cross(e2)
        det = e1.dot(pvec)
        if det < 1e-8 and det > -1e-8:
            return None

        inv_det = 1 / det
        tvec = self.origin - b
        u = tvec.dot(pvec) * inv_det
        if u < 0 or u > 1:
            return None

        qvec = tvec.cross(e1)
        v = self.direction.dot(qvec) * inv_det
        if v < 0 or u + v > 1:
            return None

        return self.at(e2.dot(qvec) * inv_det)

    def intersect_triangle(self, a, b, c):
        edge1 = a - b
        edge2 = c - b
        normal = edge1.cross(edge2)
        DdN = self.direction.dot(normal)

        if DdN > 0:
            sign = 1
        elif DdN < 0:
            sign = -1
            DdN *= -1
        else:
            return None

        diff = self.origin - a
        DdQxE2 = sign * self.direction.dot(diff.cross(edge2))

        if DdQxE2 < 0:
            return None

        DdE1xQ = sign * self.direction.dot(edge1.cross(diff))
        if DdE1xQ < 0:
            return None

        if DdQxE2 + DdE1xQ > DdN:
            return None

        QdN = -sign * diff.dot(normal)

        if QdN < 0:
            return None

        return self.at(QdN / DdN)


class Raycaster:
    """
    A class for mouse picking in 3D space. Inspiration from ThreeJS' Raycaster implementation.
    https://github.com/mrdoob/three.js/blob/master/src/core/Raycaster.js
    """

    def __init__(self, origin=None, direction=None, near=None, far=None):
        self.ray = Ray(origin, direction)
        self.near = near if near else 0
        self.far = far if far else numpy.inf

    def set_from_camera(self, coords: tuple, camera):
        self.ray.origin = camera.get_position()  # Vector3.from_matrix44_translation(camera.matrix, dtype=numpy.float32)
        self.ray.direction = camera.unproject(coords)
        self.ray.direction.normalize()

    def intersect_object(self, obj, camera) -> List[Renderable.Intersection]:
        return obj.raycast(self, camera)

    def intersect_objects(self, camera) -> List[Renderable.Intersection]:
        intersects = []
        for obj in camera.scene.objects:
            intersects += self.intersect_object(obj, camera)
        intersects.sort(key=lambda i: i.distance)
        return intersects
