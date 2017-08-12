import numpy
from typing import Optional, List

from pyrr import Vector3

from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.renderable import Renderable
from vistas.core.graphics.scene import Scene


# Todo - add tests for bounding box intersection
class Ray:
    """
    Representation of a ray in 3D space. Rays emit from an origin along a direction.
    https://github.com/mrdoob/three.js/blob/master/src/math/Ray.js
    """

    def __init__(self, origin: Optional[Vector3]=None, direction: Optional[Vector3]=None):
        self.origin = origin if origin else Vector3()
        self.direction = direction if direction else Vector3()
        self.direction.normalize()

    def at(self, t):
        """ The distance along the Ray to retrieve a position for. """

        return self.direction * t + self.origin

    def intersect_bbox(self, bbox: BoundingBox):
        """ Test if this ray intersects a bounding box. """

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

        if tmin > tymin or tymin > tmax:
            return False

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

        if tmin > tzmax or tzmax > tmax:
            return False

        if tzmin > tmin or tmin != tmin:
            tmin = tzmin

        if tzmax < tmax or tmax != tmax:
            tmax = tzmax

        # Return point closest to the ray on the positive side
        if tmax < 0:
            return False

        return self.at(tmin if tmin >= 0 else tmax)


class Raycaster:
    """
    A class for mouse picking in 3D space. Inspiration from ThreeJS' Raycaster implementation.
    https://github.com/mrdoob/three.js/blob/master/src/core/Raycaster.js
    """

    def __init__(self, origin=None, direction=None, near=None, far=None):
        self.ray = Ray(origin, direction)
        self.near = near if near else 0
        self.far = far if far else numpy.inf

    def set_from_camera(self, camera):
        pass

    def intersect_object(self, obj: Renderable) -> List[Renderable.Intersection]:
        return obj.raycast(self)

    def intersect_objects(self, scene: Scene) -> List[Renderable.Intersection]:
        intersects = []
        for obj in scene.objects:
            intersects += self.intersect_object(obj)

        # Todo - sort intersects by distance

        return intersects
