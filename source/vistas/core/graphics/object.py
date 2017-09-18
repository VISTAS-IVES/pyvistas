from pyrr import Vector3

from vistas.core.bounds import BoundingBox


class Object3D:
    """ Partially abstract class defining the base API for interacting with 3D objects. """

    def __init__(self):
        self.position = Vector3([0.] * 3)
        self.scale = Vector3([1.] * 3)
        self.rotation = Vector3([0.] * 3)

    @property
    def bounding_box(self) -> BoundingBox:
        raise NotImplementedError

    @property
    def bounding_box_world(self) -> BoundingBox:
        """ Returns the bounding box of this Object3D in coordinates relative to it's position. """

        min_x = self.bounding_box.min_x + self.position.x
        min_y = self.bounding_box.min_y + self.position.y
        min_z = self.bounding_box.min_z + self.position.z
        max_x = self.bounding_box.max_x + self.position.x
        max_y = self.bounding_box.max_y + self.position.y
        max_z = self.bounding_box.max_z + self.position.z
        return BoundingBox(min_x, min_y, min_z, max_x, max_y, max_z)

    def update(self):
        """ Update this object's internal properties. """

        pass    # Implemented by subclasses

    def raycast(self, raycaster):
        """
        Intersect this object with a camera's Raycaster and return a list of Intersections.
        Subclasses should override this method to define how each object should be interesected.
        """

        return []


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
