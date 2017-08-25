from pyrr import Vector3


class Object3D:
    """ Abstract class defining the base API for interacting with 3D objects. """

    def __init__(self):
        self.position = Vector3([0.] * 3)
        self.scale = Vector3([1.] * 3)
        self.rotation = Vector3([0.] * 3)

    def update(self):
        """ Update this object's internal properties. """

        pass    # Implemented by subclasses

    def raycast(self, raycaster):
        """ Intersect this object with a camera's Raycaster and return a list of Intersections"""

        pass    # Implemented by subclasses


class Face:
    """ Container for describing a face on an Object3D """

    def __init__(self, a, b, c, normal=None, color=None):
        self.a = a
        self.b = b
        self.c = c
        self.normal = normal
        self.color = color


class Intersection:
    """ Container for describing an intersection at a point on an Object3D """

    def __init__(self, distance, point, obj):
        self.distance = distance
        self.point = point
        self.object = obj
        self.uv = None
        self.face = None
        self.face_index = None
