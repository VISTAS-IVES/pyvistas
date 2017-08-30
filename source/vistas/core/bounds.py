from pyrr import Vector3


class BoundingBox:
    """ An interface for determining common bounding box values. """

    def __init__(self, min_x=-1, min_y=-1, min_z=-1, max_x=1, max_y=1, max_z=1):
        self.min_x = min_x
        self.min_y = min_y
        self.min_z = min_z
        self.max_x = max_x
        self.max_y = max_y
        self.max_z = max_z

    @property
    def center(self) -> Vector3:
        return Vector3([
            self.max_x - (self.max_x - self.min_x) / 2,
            self.max_y - (self.max_y - self.min_y) / 2,
            self.max_z - (self.max_z - self.min_z) / 2
        ])

    @property
    def diameter(self) -> float:
        return max(max(self.max_x - self.min_x, self.max_y - self.min_y), self.max_z - self.min_z)

    def scale(self, factor: Vector3):
        self.min_x *= factor.x
        self.max_x *= factor.x
        self.min_y *= factor.y
        self.max_y *= factor.y
        self.min_z *= factor.z
        self.max_z *= factor.z

    def move(self, distance: Vector3):
        self.min_x += distance.x
        self.max_x += distance.x
        self.min_y += distance.y
        self.max_y += distance.y
        self.min_z += distance.z
        self.max_z += distance.z

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


def union_bboxs(bboxs) -> BoundingBox:
    """ Return the largest BoundingBox from a list of bounding boxes. """

    if not bboxs:
        return BoundingBox(*[-1]*3, *[1]*3)

    bbox = bboxs[0]
    for box in bboxs[1:]:
        bbox.min_x = min(box.min_x, bbox.min_x)
        bbox.max_x = max(box.max_x, bbox.max_x)
        bbox.min_y = min(box.min_y, bbox.min_y)
        bbox.max_y = max(box.max_y, bbox.max_y)
        bbox.min_z = min(box.min_z, bbox.min_z)
        bbox.max_z = max(box.max_z, bbox.max_z)

    return bbox
