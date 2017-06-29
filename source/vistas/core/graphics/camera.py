import numpy
from OpenGL.GL import *
from PIL import Image
from pyrr import Matrix44, Vector3

from vistas.core.color import RGBColor
from vistas.core.graphics.scene import Scene


class Camera:
    offscreen_buffers_initialized = False
    offscreen_frame_buffer = None
    offscreen_color_buffer = None
    offscreen_depth_buffer = None

    def __init__(self, scene=None, color=RGBColor(0, 0, 0)):
        if scene is None:
            scene = Scene()

        self.scene = scene
        self.color = color
        self._matrix_stack = []
        self.matrix = Matrix44.identity(dtype=numpy.float32)
        self.saved_matrix_state = None
        self.wireframe = False
        self.selection_view = False
        self.proj_matrix = Matrix44.identity(dtype=numpy.float32)

        self.set_up_vector(Vector3([0, 1, 0]))
        self.set_position(Vector3())
        self.set_point_of_interest(Vector3([0, 0, -10]))

        # Todo: VI_CameraSyncObservable::GetInstance()->AddObserver(this);

    def __del__(self):
        pass  # Todo

    def push_matrix(self):
        self._matrix_stack.append(self.matrix.copy())

    def pop_matrix(self):
        if self._matrix_stack:
            self.matrix = self._matrix_stack.pop()

    def get_position(self) -> Vector3:
        mat = self.matrix
        relative_pos = Vector3([mat[3, 0], mat[3, 1], mat[3, 2]])
        relative_pos *= -1
        actual_pos = Vector3()

        for i in range(3):
            actual_pos[i] = mat[i, 0] * relative_pos.x + mat[i, 1] * relative_pos.y + mat[i, 2] * relative_pos.z

        return actual_pos

    def get_direction(self) -> Vector3:
        return Vector3([self.matrix[0, 2] * -1, self.matrix[1, 2] * -1, self.matrix[2, 2] * -1])

    def set_point_of_interest(self, poi: Vector3):
        self.matrix = Matrix44.look_at(self.get_position(), poi, self.get_up_vector())

    def look_at(self, eye, target, up):
        self.matrix = Matrix44.look_at(eye, target, up)

    def set_position(self, position: Vector3):
        relative_pos = self.matrix * position * -1
        self.matrix[3, 0] = relative_pos.x
        self.matrix[3, 1] = relative_pos.y
        self.matrix[3, 2] = relative_pos.z

    def get_up_vector(self) -> Vector3:
        return Vector3([self.matrix[0, 1], self.matrix[1, 1], self.matrix[2, 1]])

    def set_up_vector(self, up: Vector3):
        unit_up = up.copy()
        unit_up.normalise()
        pos = self.get_position()

        self.matrix[0, 1] = unit_up.x
        self.matrix[1, 1] = unit_up.y
        self.matrix[2, 1] = unit_up.z

        right = self.get_direction().cross(unit_up)
        right.normalise()
        self.matrix[0, 0] = right.x
        self.matrix[1, 0] = right.y
        self.matrix[2, 0] = right.z

        forward = unit_up.cross(right)
        forward.normalise()
        self.matrix[0, 2] = forward.x * -1
        self.matrix[1, 2] = forward.y * -1
        self.matrix[2, 2] = forward.z * -1

        self.set_position(pos)

    def move_relative(self, movement):
        self.matrix *= Matrix44.from_translation(movement)

    def rotate_relative(self, rotation):
        pos = self.get_position()
        rotate_matrix = Matrix44.from_x_rotation(rotation.x) * \
                        Matrix44.from_y_rotation(rotation.y) * \
                        Matrix44.from_z_rotation(rotation.z)
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
            self.scene.render(self)

    def render_to_bitmap(self, width, height):
        if not Camera.offscreen_buffers_initialized:
            Camera.offscreen_frame_buffer = glGenFramebuffers(1)
            Camera.offscreen_color_buffer = glGenRenderbuffers(1)
            Camera.offscreen_depth_buffer = glGenRenderbuffers(1)
            Camera.offscreen_buffers_initialized = True

        glBindFramebuffer(GL_FRAMEBUFFER, Camera.offscreen_frame_buffer)
        glBindRenderbuffer(GL_RENDERBUFFER, Camera.offscreen_depth_buffer)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT, width, height)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, Camera.offscreen_depth_buffer)
        glBindRenderbuffer(GL_RENDERBUFFER, Camera.offscreen_color_buffer)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_RGBA, width, height)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_RENDERBUFFER, Camera.offscreen_color_buffer)

        self.render(width, height)

        glPixelStorei(GL_PACK_ALIGNMENT, 1)
        image_data = glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        return Image.frombuffer('RGBA', (width, height), image_data)

    def select_object(self, width, height, x, y):
        pass  # Todo

    def update(self, observable):
        pass  # Todo

    def reset(self, width, height, color):
        # scene_box = self.scene.bounding_box

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        glClearDepth(1.0)
        glClear(GL_DEPTH_BUFFER_BIT)
        glClearColor(color.r, color.g, color.b, color.a)
        glClear(GL_COLOR_BUFFER_BIT)

        glViewport(0, 0, width, height)

        # c = (self.matrix * Vector(*scene_box.center.v[:3], 1))     # Todo - fix z_near/z_far calculations or remove?
        # z_near = max(1, c.z - scene_box.diameter / 2)
        # z_far = (c.z + scene_box.diameter) * 2
        # self.proj_matrix = ViewMatrix.perspective(80.0, width / height, z_near, z_far)

        self.proj_matrix = Matrix44.perspective_projection(80.0, width / height, 1, 100000)
