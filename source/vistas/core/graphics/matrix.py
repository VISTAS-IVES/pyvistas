import math

import numpy
from OpenGL.GL import *

from vistas.core.graphics.vector import Vector


class ViewMatrix:
    def __init__(self):
        self.m = numpy.matrix('1 0 0 0; 0 1 0 0; 0 0 1 0; 0 0 0 1', dtype=numpy.float32)  # Identity matrix
        self.stack = []

    def __getitem__(self, item):
        return self.m[item]

    def __setitem__(self, key, value):
        self.m[key] = value

    def __mul__(self, other):
        if isinstance(other, ViewMatrix):
            m = ViewMatrix()
            m.m = self.m * other.m

            return m

        elif isinstance(other, Vector):
            v = (self.m * other.v.reshape(4, 1)).reshape(1, 4).A[0]
            return Vector(*v)

        else:
            raise ValueError("Can't multiply matrix with {}".format(other.__class__.__name__))

    @classmethod
    def from_gl(cls, mode):
        matrix = glGetFloatv(mode)
        obj = cls()
        obj.m = numpy.matrix(matrix.reshape(4, 4), dtype=numpy.float32)

        return obj

    def push(self):
        self.stack.insert(0, self.m.copy())

    def pop(self):
        if self.stack:
            self.m = self.stack.pop()

    def transpose(self):
        t = ViewMatrix()
        t.m = self.m.T

        return t

    def __sub__(self, other):
        result = ViewMatrix()
        result.m = self.m - other.m

        return result

    def __add__(self, other):
        result = ViewMatrix()
        result.m = self.m = other.m

        return result

    @property
    def gl(self):
        return self.m.A1

    @staticmethod
    def translate(x, y, z):
        t = ViewMatrix()
        t[3, 0] = x
        t[3, 1] = y
        t[3, 2] = z

        return t

    @staticmethod
    def scale(x, y, z):
        t = ViewMatrix()
        t[0, 0] = x
        t[1, 1] = y
        t[2, 2] = z

        return t

    @staticmethod
    def rotate_x(degrees):
        radians = math.radians(degrees)

        r = ViewMatrix()
        r[2, 2] = r[1,1] = math.cos(radians)
        r[1, 2] = math.sin(radians)
        r[2, 1] = -1 * r[1,2]

        return r

    @staticmethod
    def rotate_y(degrees):
        radians = math.radians(degrees)

        r = ViewMatrix()
        r[2, 2] = r[0,0] = math.cos(radians)
        r[2, 0] = math.sin(radians)
        r[0, 2] = -1 * r[2,0]

        return r

    @staticmethod
    def rotate_z(degrees):
        radians = math.radians(degrees)

        r = ViewMatrix()
        r[0, 0] = r[1,1] = math.cos(radians)
        r[0, 1] = math.sin(radians)
        r[1, 0] = -1 * r[0,1]

        return r

    @staticmethod
    def perspective(fovy, aspect, z_near, z_far):
        result = ViewMatrix()

        top = math.tan(math.radians(fovy)/2) * z_near
        right = top * aspect

        result[0, 0] = z_near / right
        result[1, 1] = z_near / top
        result[2, 2] = -1 * (z_far+z_near) / (z_far-z_near)
        result[3, 2] = -2*z_far*z_near / (z_far-z_near)
        result[2, 3] = -1
        result[3, 3] = 0

        return result
