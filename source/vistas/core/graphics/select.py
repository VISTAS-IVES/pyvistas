import numpy
from pyrr import Vector3

from vistas.core.graphics.line import BoxLineGeometry, PolygonLineGeometry
from vistas.core.graphics.mesh import Mesh
from vistas.core.graphics.simple import Box, BasicShaderProgram


class SelectBase:
    """ Object-level selection via grouping """

    def __init__(self, raycaster, camera):
        self.raycaster = raycaster
        self.camera = camera
        self.points = []
        self.width = 800
        self.height = 600
        self.line_mesh = None
        self.start_intersect = None

    def reset(self):
        for p in self.points:
            p.geometry.dispose()
        del self.points[:]
        self.start_intersect = None
        if self.line_mesh:
            self.line_mesh.geometry.dispose()
            self.line_mesh = None

    @property
    def coords(self):
        return [(p.position.x, p.position.y) for p in self.points]

    @property
    def plugin(self):
        if self.start_intersect:
            return self.start_intersect.object.plugin
        return None

    def render(self, camera):
        for point in self.points:
            camera.push_matrix()
            point.render(camera)
            camera.pop_matrix()
        if self.line_mesh:
            self.line_mesh.render(camera)


class BoxSelect(SelectBase):
    """ Box-defined selection """

    def __init__(self, raycaster, camera):
        super().__init__(raycaster, camera)
        self.start = None

    def reset(self):
        super().reset()
        self.start = None

    def from_screen_coords(self, start, current):
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

            lb = [left, bottom, self.plugin.get_height_at_point((left, bottom))]
            rb = [right, bottom, self.plugin.get_height_at_point((right, bottom))]
            rt = [right, top, self.plugin.get_height_at_point((right, top))]
            lt = [left, top, self.plugin.get_height_at_point((left, top))]
            self.points[0].position = Vector3(lb)
            self.points[1].position = Vector3(rb)
            self.points[2].position = Vector3(rt)
            self.points[3].position = Vector3(lt)

            vertices = numpy.array([
                    *lb, *rb, *rt, *lt
                ], dtype=numpy.float32)

            if not self.line_mesh:
                linegeo = BoxLineGeometry(vertices=vertices)
                self.line_mesh = Mesh(linegeo, BasicShaderProgram())
            else:
                self.line_mesh.geometry.vertices = vertices
                self.line_mesh.geometry.compute_bounding_box()
                self.line_mesh.update()


class PolySelect(SelectBase):
    """ User-defined polygon selection """

    def _add_box(self, box):
        self.points.append(box)
        self._reset_linemesh()

    def _reset_linemesh(self):
        if self.line_mesh:
            self.line_mesh.geometry.dispose()
            self.line_mesh = None
        if self.points:
            linegeo = PolygonLineGeometry(
                len(self.points), numpy.array([b.position for b in self.points], dtype=numpy.float32)
            )
            self.line_mesh = Mesh(linegeo, BasicShaderProgram())

    def append_point(self, x, y):
        mouse_x = x / self.width * 2 - 1
        mouse_y = - y / self.height * 2 + 1
        intersects = self.raycaster.intersect_objects((mouse_x, mouse_y), self.camera)
        if intersects:
            if not self.start_intersect:
                self.start_intersect = intersects[0]
            box = Box()
            box.position = intersects[0].point
            self._add_box(box)

    def remove_last(self):
        if self.points:
            p = self.points.pop()
            p.geometry.dispose()
            del p
            self._reset_linemesh()

    def close_loop(self):
        if self.points:
            self._add_box(self.points[0])
