from vistas.core.graphics.vector import Vector


class BoundingBox:
    def __init__(self, min_x, min_y, min_z, max_x, max_y, max_z):
        self.min_x = min_x
        self.min_y = min_y
        self.min_z = min_z
        self.max_x = max_x
        self.max_y = max_y
        self.max_z = max_z

    @property
    def center(self):
        return Vector(
            self.max_x - (self.max_x-self.min_x)/2,
            self.max_y - (self.max_y-self.min_y)/2,
            self.max_z - (self.max_z-self.min_z)/2
        )

    @property
    def diameter(self):
        return max(max(self.max_x-self.min_x, self.max_y-self.min_y), self.max_z-self.min_z)

    def scale(self, factor: Vector):
        self.min_x *= factor.x
        self.max_x *= factor.x
        self.min_y *= factor.y
        self.max_y *= factor.y
        self.min_z *= factor.z
        self.max_z *= factor.z

    def move(self, distance: Vector):
        self.min_x += distance.x
        self.max_x += distance.x
        self.min_y += distance.y
        self.max_y += distance.y
        self.min_z += distance.z
        self.max_z += distance.z

