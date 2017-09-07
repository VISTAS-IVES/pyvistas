from typing import Optional, List

import numpy
from pyrr import Matrix44, Vector3

from vistas.core.bounds import BoundingBox
from vistas.core.graphics.object import Object3D, Intersection


class Ray:
    """
    Representation of a ray in 3D space. Rays emit from an origin along a direction. Implementation inspired by mrdoob -
    https://github.com/mrdoob/three.js/blob/master/src/math/Ray.js
    """

    def __init__(self, origin: Optional[Vector3]=None, direction: Optional[Vector3]=None):
        self.origin = origin if origin is not None else Vector3()
        self.direction = direction if direction is not None else Vector3()
        self.direction.normalize()

    def at(self, t):
        """ Retrieve a point along the ray. """

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

        if tymin > tmin or tmin != tmin:    # tmin != tmin returns false if t_min is numpy.inf
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

    def intersect_triangles(self, a, b, c):
        """ Determine face-level triangle intersections from this ray. """
        e1 = b - a
        e2 = c - a
        direction = numpy.array(self.direction)
        origin = numpy.array(self.origin)
        eps = numpy.finfo(numpy.float32).eps

        pvec = numpy.cross(direction, e2)
        det = numpy.sum(e1 * pvec, axis=-1)
        det_cond = (det >= eps) | (det <= -eps)     # Get values outside of range -eps < det < eps

        inv_det = 1 / det
        tvec = origin - a
        u = numpy.sum(tvec * pvec, axis=-1) * inv_det
        u_cond = (u <= 1) & (u >= 0)                    # Get values if not (u < 0 or u > 1)

        qvec = numpy.cross(tvec, e1)
        v = numpy.sum(direction * qvec, axis=-1) * inv_det
        v_cond = (v >= 0) & (u + v <= 1)                    # Get values if not (if v < 0 or u + v > 1)

        # Filter down and determine intersections
        result = numpy.sum(e2 * qvec, axis=-1) * inv_det
        intersections = numpy.where(det_cond & u_cond & v_cond)
        distances = result[intersections]

        # Now we return their locations in terms of distance
        return distances, intersections[0]


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
        """ Update the Raycaster's ray to extend from the given Camera. """

        self.ray.origin = camera.get_position()
        self.ray.direction = camera.unproject(coords)
        self.ray.direction.normalize()

    def intersect_object(self, coords, obj, camera) -> List[Intersection]:
        """ Retrieve intersections, sorted in ascending distance, to a given Object3D. """

        intersects = []
        if issubclass(obj.__class__, Object3D):
            camera.push_matrix()
            self.set_from_camera(coords, camera)
            camera.matrix *= Matrix44.from_translation(obj.position)
            intersects = obj.raycast(self)
            camera.pop_matrix()
            if intersects:
                intersects.sort(key=lambda i: i.distance)
        return intersects

    def intersect_objects(self, coords: tuple, camera) -> List[Intersection]:
        """ Retrieve intersections to all Object3D objects in a given Camera's Scene. """

        intersects = []
        for obj in camera.scene.objects:
            intersects += self.intersect_object(coords, obj, camera)
        if intersects:
            intersects.sort(key=lambda i: i.distance)
        return intersects
