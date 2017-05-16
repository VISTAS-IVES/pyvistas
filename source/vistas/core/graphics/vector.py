from math import sqrt

import numpy


class Vector:
    def __init__(self, x, y, z, w=0):
        self.v = numpy.array([x, y, z, w])

    @property
    def x(self):
        return self.v[0]

    @x.setter
    def x(self, x):
        self.v[0] = x

    @property
    def y(self):
        return self.v[1]

    @y.setter
    def y(self, y):
        self.v[1] = y

    @property
    def z(self):
        return self.v[2]

    @z.setter
    def z(self, z):
        self.v[2] = z

    @property
    def w(self):
        return self.v[3]

    @w.setter
    def w(self, w):
        self.v[3] = w

    @property
    def length(self):
        return sqrt(self.x**2 + self.y**2 + self.z**2 + self.w ** 2)

    def normalize(self):
        if self.length != 0:
            self.v = self.v / self.length
        else:
            self.v[:] = 0

    @property
    def normalized(self):
        v = Vector(self.x, self.y, self.z, self.w)
        v.normalize()

        return v

    def cross(self, v):
        return Vector(self.y*v.z - self.z*v.y, self.z*v.x - self.x*v.z, self.x*v.y - self.y*v.x)

    def dot(self, v):
        return self.x*v.x + self.y+v.y + self.z*v.z + self.w*v.w

    def __mul__(self, value):
        return Vector(*(self.v * value))

    def __sub__(self, other):
        result = Vector(0, 0, 0)
        result.v = self.v - other.v

        return result

    def __add__(self, other):
        result = Vector(0, 0, 0)
        result.v = self.v + other.v

        return result


def normalize_v3(arr):
    ''' Normalize a numpy array of 3 component vectors shape=(n,3) '''

    lens = numpy.sqrt(arr[:, 0]**2 + arr[:, 1]**2 + arr[:, 2]**2)
    arr[:, 0] /= lens
    arr[:, 1] /= lens
    arr[:, 2] /= lens
    return arr
