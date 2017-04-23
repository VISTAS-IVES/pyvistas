from OpenGL.GL import *

from vistas.core.color import RGBColor
from vistas.core.graphics.bounds import BoundingBox


class Scene:
    def __init__(self, name='New Scene'):
        self.render_bounding_boxes = False
        self.bounding_box_color = RGBColor(1, 1, 1)
        self.name = name
        self.objects = []

    def add_object(self, obj):
        self.objects.append(obj)

    def remove_object(self, obj):
        self.objects.remove(obj)

    def remove_all_objects(self):
        self.objects = []

    @property
    def bounding_box(self):
        if not self.objects:
            return BoundingBox(0, 0, 0, 0, 0, 0)

        bbox = self.objects[0].bounding_box
        for obj in self.objects[1:]:
            bbox.min_x = min(obj.bounding_box.min_x, bbox.min_x)
            bbox.max_x = max(obj.bounding_box.max_x, bbox.max_x)
            bbox.min_y = min(obj.bounding_box.min_y, bbox.min_y)
            bbox.max_y = max(obj.bounding_box.max_y, bbox.max_y)
            bbox.min_z = min(obj.bounding_box.min_z, bbox.min_z)
            bbox.max_z = max(obj.bounding_box.max_z, bbox.max_z)

        return bbox

    def render(self):
        for obj in self.objects:
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()

            obj.render()

            if self.render_bounding_boxes:
                obj.render_bounding_box(self.bounding_box_color)

            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()

    def select_object(self, x, y):
        pass  # Todo

    def has_object(self, obj):
        return obj in self.objects
