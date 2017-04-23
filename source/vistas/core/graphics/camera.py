import math

import numpy
from OpenGL.GL import *

from vistas.core.color import RGBColor
from vistas.core.graphics.scene import Scene
from vistas.core.graphics.vector import Vector


class ViewMatrix:
    def __init__(self):
        self.m = numpy.matrix('1 0 0 0; 0 1 0 0; 0 0 1 0; 0 0 0 1', dtype='f')  # Identity matrix

    def __getitem__(self, item):
        return self.m[item]

    def __setitem__(self, key, value):
        self.m[key] = value

    def __mul__(self, other):
        if isinstance(other, ViewMatrix):
            m = ViewMatrix()
            m.m = self.m * other.m

            return m

        elif isinstance(other, Vector):
            v = (self.m * other.v.reshape(4, 1)).reshape(1, 4).A[0]
            return Vector(*v)

        else:
            raise ValueError("Can't multiply matrix with {}".format(other.__class__.__name__))

    def transpose(self):
        t = ViewMatrix()
        t.m = self.m.T

        return t

    def __sub__(self, other):
        result = ViewMatrix()
        result.m = self.m - other.m

        return result

    def __add__(self, other):
        result = ViewMatrix()
        result.m = self.m = other.m

        return result

    @property
    def gl(self):
        return self.m.A1

    @staticmethod
    def translate(x, y, z):
        t = ViewMatrix
        t[3,0] = x
        t[3,1] = y
        t[3,2] = z

        return t

    @staticmethod
    def rotate_x(degrees):
        radians = math.radians(degrees)

        r = ViewMatrix()
        r[2,2] = r[1,1] = math.cos(radians)
        r[1,2] = math.sin(radians)
        r[2,1] = -1 * r[1,2]

        return r

    @staticmethod
    def rotate_y(degrees):
        radians = math.radians(degrees)

        r = ViewMatrix()
        r[2,2] = r[0,0] = math.cos(radians)
        r[2,0] = math.sin(radians)
        r[0,2] = -1 * r[2,0]

        return r

    @staticmethod
    def rotate_z(degrees):
        radians = math.radians(degrees)

        r = ViewMatrix()
        r[0,0] = r[1,1] = math.cos(radians)
        r[0,1] = math.sin(radians)
        r[1,0] = -1 * r[0,1]

        return r

    @staticmethod
    def perspective(fovy, aspect, z_near, z_far):
        result = ViewMatrix()

        top = math.tan(math.radians(fovy)/2) * z_near
        right = top * aspect

        result[0,0] = z_near / right
        result[1,1] = z_near / top
        result[2,2] = -1 * (z_far+z_near) / (z_far-z_near)
        result[3,2] = -2*z_far*z_near / (z_far-z_near)
        result[2,3] = -1
        result[3,3] = 0

        return result


class Camera:
    def __init__(self, scene=None, color=RGBColor(0, 0, 0)):
        if scene is None:
            scene = Scene()

        self.scene = scene
        self.color = color
        self.matrix = ViewMatrix()
        self.saved_matrix_state = None
        self.wireframe = False
        self.selection_view = False
        self.z_near_plane = 1
        self.proj_matrix = ViewMatrix()

        self.set_up_vector(Vector(0, 1, 0))
        self.set_position(Vector(0, 0, 0))
        self.set_point_of_interest(Vector(0, 0, -10))

        # Todo: VI_CameraSyncObservable::GetInstance()->AddObserver(this);

    def __del__(self):
        pass  # Todo

    def get_position(self):
        relative_pos = Vector(self.matrix[3,0], self.matrix[3,1], self.matrix[3,2])
        relative_pos *= -1

        actual_pos = Vector(0, 0, 0)
        for i, attr in enumerate(['x','y','z']):
            setattr(
                actual_pos, attr,
                self.matrix[i,0]*relative_pos.x + self.matrix[i,1]*relative_pos.y + self.matrix[i,2]*relative_pos.z
            )

        return actual_pos

    def get_direction(self):
        return Vector(self.matrix[0,2]*-1, self.matrix[1,2]*-1, self.matrix[2,2]*-1)

    def set_point_of_interest(self, poi):
        pos = self.get_position()
        forward = poi - pos
        forward.normalize()

        right = forward.cross(self.get_up_vector())
        right.normalize()

        up = right.cross(forward)
        up.normalize()

        self.matrix[0,0] = right.x
        self.matrix[1,0] = right.y
        self.matrix[2,0] = right.z

        self.matrix[0,1] = up.x
        self.matrix[1,1] = up.y
        self.matrix[2,1] = up.z

        self.matrix[0,2] = forward.x * -1
        self.matrix[1,2] = forward.y * -1
        self.matrix[2,2] = forward.z * -1

        self.set_position(pos)

    def set_position(self, position):
        relative_pos = self.matrix * position * -1
        self.matrix[3,0] = relative_pos.x
        self.matrix[3,1] = relative_pos.y
        self.matrix[3,2] = relative_pos.z

    def get_up_vector(self):
        return Vector(self.matrix[0,1], self.matrix[1,1], self.matrix[2,1])

    def set_up_vector(self, up):
        unit_up = up.normalized
        pos = self.get_position()

        self.matrix[0,1] = unit_up.x
        self.matrix[1,1] = unit_up.y
        self.matrix[2,1] = unit_up.z

        right = self.get_direction().cross(unit_up)
        right.normalize()
        self.matrix[0,0] = right.x
        self.matrix[1,0] = right.y
        self.matrix[2,0] = right.z

        forward = unit_up.cross(right)
        forward.normalize()
        self.matrix[0,2] = forward.x * -1
        self.matrix[1,2] = forward.y * -1
        self.matrix[2,2] = forward.z * -1

        self.set_position(pos)

    def move_relative(self, movement):
        self.matrix *= ViewMatrix.translate(*movement.v[:3])

    def rotate_relative(self, rotation):
        pos = self.get_position()
        rotate_matrix = (
            ViewMatrix.rotate_x(rotation.x) * ViewMatrix.rotate_y(rotation.y) * ViewMatrix.rotate_z(rotation.z)
        )

        self.matrix = rotate_matrix * self.matrix
        self.set_position(pos)

    def distance_to_point(self, point):
        return abs((point - self.get_position()).length)

    def distance_to_object(self, obj):
        return abs((obj.bounds.center - self.get_position()).length)

    def render(self, width, height):
        if self.selection_view:
            self.reset(width, height, RGBColor(1, 1, 1, 1))
        else:
            self.reset(width, height, self.color)

        # Render scene
        if self.wireframe:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        else:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        if self.selection_view:
            self.scene.select_object(0, 0)
        else:
            self.scene.render()

    def render_to_bitmap(self, width, height):
        pass  # Todo

    def select_object(self, width, height, x, y):
        pass  # Todo

    def update(self, observable):
        pass # Todo

    def reset(self, width, height, color):
        scene_box = self.scene.bounding_box

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        glClearDepth(1.0)
        glClear(GL_DEPTH_BUFFER_BIT)
        glClearColor(color.r, color.g, color.b, color.a)
        glClear(GL_COLOR_BUFFER_BIT)

        glViewport(0, 0, width, height)

        c = (self.matrix * Vector(*scene_box.center.v[:3], 1)) * -1
        z_near = max(1, c.z - scene_box.diameter / 2)
        z_far = c.z + scene_box.diameter

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glLoadMatrixf(self.matrix.gl)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glLoadMatrixf(ViewMatrix.perspective(80.0, width / height, z_near, z_far).gl)
