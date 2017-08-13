from typing import Optional
from pyrr import Matrix44, Vector3


def cubic_interpolation(p0: Vector3, p1: Vector3, p2: Vector3, p3: Vector3, t) -> Vector3:
    """ Calculate the cubic interpolation between 3 vectors as a vector along the parametric parameter t. """
    t2 = t * t
    a = p3 - p2 - p0 + p1
    return a * t * t2 + (p0 - p1 - a) * t2 + (p2 - p0) * t + p1


def catmull_rom_splines(p0: Vector3, p1: Vector3, p2: Vector3, p3: Vector3, t) -> Vector3:
    """ Calculate the catmull rom spline between 3 vectors as a vector along the parametric parameter t. """
    t2 = t * t
    a0 = p0 * -0.5 + p1 * 1.5 + p2 * -1.5 + p3 * 0.5
    a1 = p0 - p1 * 2.5 + p2 * 2.0 - p3 * 0.5
    a2 = p0 * -0.5 + p2 * 0.5
    a3 = p1
    return a0 * t * t2 + a1 * t2 + a2 * t + a3


def apply_matrix_44(vec: Vector3, m: Matrix44):
    v = vec.copy()
    x, y, z = v
    w = 1 / (m.m14 * x + m.m24 * y + m.m34 * z + m.m44)
    v.x = (m.m11 * x + m.m21 * y + m.m31 * z + m.m41) * w
    v.y = (m.m12 * x + m.m22 * y + m.m32 * z + m.m42) * w
    v.z = (m.m13 * x + m.m23 * y + m.m33 * z + m.m43) * w
    return v


def transform_direction(vec: Vector3, m: Matrix44):
    v = vec.copy()
    x, y, z = v
    v.x = m.m11 * x + m.m21 * y + m.m31 * z
    v.y = m.m12 * x + m.m22 * y + m.m32 * z
    v.z = m.m13 * x + m.m23 * y + m.m33 * z
    v.normalize()
    return v


class Triangle:
    """
    Barymetric coordinate math within a triangle defined in 3D space.
    Borrowed from https://github.com/mrdoob/three.js/blob/master/src/math/Triangle.js
    """

    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c

    @property
    def normal(self):
        pass

    def barycoord_from_pos(self, p):
        return Triangle._barycoord_from_pos(p, self.a, self.b, self.c)

    def contains_point(self, p):
        return Triangle._contains_point(p, self.a, self.b, self.c)

    @staticmethod
    def _barycoord_from_pos(p, a, b, c) -> Optional[Vector3]:
        v0 = c - a
        v1 = b - a
        v2 = p - a

        dot00 = v0.dot(v0)
        dot01 = v0.dot(v1)
        dot02 = v0.dot(v2)
        dot11 = v1.dot(v1)
        dot12 = v1.dot(v2)
        denom = (dot00 * dot11 - dot01 * dot01)

        if denom == 0:
            return None

        inv_denom = 1 / denom
        u = (dot11 * dot02 - dot01 * dot12) * inv_denom
        v = (dot00 * dot12 - dot01 * dot02) * inv_denom

        return Vector3([1 - u - v, v, u])

    @staticmethod
    def _contains_point(p, a, b, c):
        result = Triangle._barycoord_from_pos(p, a, b, c)
        if result is not None:
            return result.x >= 0 and result.y >= 0 and result.x + result.y <= 1
        else:
            return False
