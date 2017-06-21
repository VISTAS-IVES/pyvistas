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

    def select_object(self, x, y):
        pass  # Todo

    def has_object(self, obj):
        return obj in self.objects
