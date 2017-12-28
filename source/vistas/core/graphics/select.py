from shapely.geometry import LinearRing, Point


class SelectBase:
    """ Object-level selection via grouping """

    def __init__(self, raycaster, camera):
        self.raycaster = raycaster
        self.camera = camera
        self.coords = []
        self.width = 800
        self.height = 600
        self.start_intersect = None

    def reset(self):
        self.start_intersect = None
        del self.coords[:]

    @property
    def plugin(self):
        if self.start_intersect:
            return self.start_intersect.object.plugin
        return None

    def update_mesh_boundary(self):
        poly = None
        if len(self.coords) > 0:
            if len(self.coords) == 1:
                poly = Point(self.coords[0])
            else:
                poly = LinearRing(self.coords + [self.coords[0]])
        self.plugin.update_zonal_boundary(poly)


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

            self.coords = [
                (left, bottom),
                (right, bottom),
                (right, top),
                (left, top)
            ]

            self.update_mesh_boundary()


class PolySelect(SelectBase):
    """ User-defined polygon selection """

    def append_point(self, x, y):
        mouse_x = x / self.width * 2 - 1
        mouse_y = - y / self.height * 2 + 1
        intersects = self.raycaster.intersect_objects((mouse_x, mouse_y), self.camera)
        if intersects:
            if not self.start_intersect:
                self.start_intersect = intersects[0]
            self.coords.append((intersects[0].point.x, intersects[0].point.y))
            self.update_mesh_boundary()

    def remove_last(self):
        if self.coords:
            self.coords.pop()
        self.update_mesh_boundary()

    def close_loop(self):
        if self.coords:
            self.coords.append(self.coords[0])
            self.update_mesh_boundary()
