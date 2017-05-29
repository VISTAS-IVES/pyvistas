import copy

from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.vector import Vector


class Renderable:
    def __init__(self):
        self.scale = Vector(1, 1, 1)
        self.position = Vector(0, 0, 0)
        self.rotation = Vector(0, 0, 0)
        self.bounding_box = BoundingBox(0, 0, 0, 0, 0, 0)

    def render(self, camera):
        pass

    def render_bounding_box(self, color, camera):
        pass  # Todo

    def render_for_selection_hit(self, color):
        pass  # Todo

    def get_selection_detail(self, width, height, x, y, camera):
        pass  # Todo

    @property
    def bounds(self):
        bounding_box = copy.copy(self.bounding_box)

        bounding_box.scale(self.scale)
        bounding_box.move(self.position)

        return bounding_box
