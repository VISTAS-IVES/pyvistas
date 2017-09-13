import numpy
from OpenGL.GL import *
from pyrr import Vector3
from vistas.core.graphics.simple import Box
# Todo - add lines connecting the boxes


# Todo - Combine BoxSelect and PolySelect?


class BoxSelect:
    def __init__(self, raycaster, camera):
        self.raycaster = raycaster
        self.camera = camera
        self.points = []
        self.width = 800
        self.height = 600
        self.start = None
        self.start_intersect = None

    def reset(self):
        for p in self.points:
            p.geometry.dispose()
        del self.points[:]
        self.start = None
        self.start_intersect = None

    @property
    def coords(self):
        return [(p.position.x, p.position.y) for p in self.points]

    @property
    def plugin(self):
        if self.start_intersect:
            return self.start_intersect.object.plugin
        return None

    def from_screen_coords(self, start=(-1, -1), current=(-1, -1)):

        def coords(x, y):
            mouse_x = x / self.width * 2 - 1
            mouse_y = - y / self.height * 2 + 1
            return mouse_x, mouse_y

        if not self.start or self.start != start:

            # Check that the starting screen coordinate lands on the terrain
            start_intersects = self.raycaster.intersect_objects(coords(*start), self.camera)
            if not start_intersects:
                return  # No hits, nothing to be done

            self.start = start
            self.start_intersect = start_intersects[0]

        # Check that the current point lands on the terrain
        current_intersects = self.raycaster.intersect_objects(coords(*current), self.camera)
        if current_intersects:
            current_intersect = current_intersects[0]

            if current_intersect.object != self.start_intersect.object:
                return

            # Now determine Box positions in world space
            start_point = self.start_intersect.point
            current_point = current_intersect.point

            if start_point.x <= current_point.x:
                left = start_point.x
                right = current_point.x
            else:
                left = current_point.x
                right = start_point.x

            if start_point.y <= current_point.y:
                top = start_point.y
                bottom = current_point.y
            else:
                top = current_point.y
                bottom = start_point.y

            if not self.points:
                self.points = [Box() for _ in range(4)]

            z = max(current_point.z, start_point.z) # Todo - any way to get 'z' for each point without perform raycast?
            self.points[0].position = Vector3([left, bottom, z])
            self.points[1].position = Vector3([right, bottom, z])
            self.points[2].position = Vector3([right, top, z])
            self.points[3].position = Vector3([left, top, z])

    def render(self, camera):
        for point in self.points:
            camera.push_matrix()
            point.render(camera)
            camera.pop_matrix()


class PolySelect:

    def __init__(self, raycaster, camera):
        self.raycaster = raycaster
        self.camera = camera
        self.width = 800
        self.height = 600
        self.points = []    # List[Box]
        self.start_intersect = None

    @property
    def coords(self):
        return [(p.position.x, p.position.y) for p in self.points]

    def reset(self):
        for p in self.points:
            p.geometry.dispose()
        del self.points[:]
        self.start_intersect = None

    @property
    def plugin(self):
        if self.start_intersect:
            return self.start_intersect.object.plugin
        return None

    def append_point(self, x, y):
        mouse_x = x / self.width * 2 - 1
        mouse_y = - y / self.height * 2 + 1
        intersects = self.raycaster.intersect_objects((mouse_x, mouse_y), self.camera)
        if intersects:
            if not self.start_intersect:
                self.start_intersect = intersects[0]
            box = Box()
            box.position = intersects[0].point
            self.points.append(box)

    def remove_last(self):
        if self.points:
            p = self.points.pop()
            p.geometry.dispose()
            del p

    def render(self, camera):
        for point in self.points:
            camera.push_matrix()
            point.render(camera)
            camera.pop_matrix()
