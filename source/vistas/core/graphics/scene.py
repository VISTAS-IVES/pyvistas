import struct

from OpenGL.GL import *
from pyrr import Matrix44

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
            return BoundingBox(-1, -1, -1, 1, 1, 1)

        bbox = self.objects[0].bounds
        for obj in self.objects[1:]:
            bbox.min_x = min(obj.bounds.min_x, bbox.min_x)
            bbox.max_x = max(obj.bounds.max_x, bbox.max_x)
            bbox.min_y = min(obj.bounds.min_y, bbox.min_y)
            bbox.max_y = max(obj.bounds.max_y, bbox.max_y)
            bbox.min_z = min(obj.bounds.min_z, bbox.min_z)
            bbox.max_z = max(obj.bounds.max_z, bbox.max_z)

        return bbox

    def render(self, camera):
        for obj in self.objects:
            camera.push_matrix()
            camera.matrix *= Matrix44.from_translation(obj.position) * Matrix44.from_scale(obj.scale)
            obj.render(camera)
            if self.render_bounding_boxes:
                obj.render_bounding_box(self.bounding_box_color, camera)
            camera.pop_matrix()

    def select_object(self, camera, x, y):

        red = green = blue = 8

        def make_mask(bits):
            return 0xFFFFFFFF >> (32 - bits)

        red_mask = make_mask(red) << (green + blue)
        green_mask = make_mask(green) << blue
        blue_mask = make_mask(blue)

        red_shift = green + blue
        green_shift = blue

        for i, obj in enumerate(self.objects):
            r = ((i & red_mask) >> red_shift) / 255.0
            g = ((i & green_mask) >> green_shift) / 255.0
            b = (i & blue_mask) / 255.0

            camera.push_matrix()
            camera.matrix *= Matrix44.from_translation(obj.position) * Matrix44.from_scale(obj.scale)
            obj.render_for_selection_hit(camera, r, g, b)
            camera.pop_matrix()

        data = struct.unpack('b'*3, glReadPixels(x, y, 1, 1, GL_RGB, GL_UNSIGNED_BYTE))
        index = (data[0] << red_shift) | (data[1] << green_shift) | data[2]
        print(index)
        if self.objects and 0 <= index < len(self.objects):
            return self.objects[index]

        return None

    def has_object(self, obj):
        return obj in self.objects
