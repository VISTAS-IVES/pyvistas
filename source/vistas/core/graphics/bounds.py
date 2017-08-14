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
    def diameter(self):
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


def union_bboxs(bboxs):
    """ Return the largest BoundingBox from a list of bounding boxes. """

    bbox = BoundingBox(bboxs[0].min_x, bboxs[0].min_y, bboxs[0].min_z, bboxs[0].max_x, bboxs[0].max_y, bboxs[0].max_z)
    for box in bboxs[1:]:
        if box.min_x < bbox.min_x:
            bbox.min_x = box.min_x
        if box.min_y < bbox.min_y:
            bbox.min_y = box.min_y
        if box.min_z < bbox.min_z:
            bbox.min_z = box.min_z
        if box.max_x > bbox.max_x:
            bbox.max_x = box.max_x
        if box.max_y > bbox.max_y:
            bbox.max_y = box.max_y
        if box.max_z > bbox.max_z:
            bbox.max_z = box.max_z
    return bbox
