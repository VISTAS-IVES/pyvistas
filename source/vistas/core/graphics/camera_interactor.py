import numpy
import math
from pyrr import Matrix44, Vector3
from vistas.core.graphics.camera import Camera
from vistas.ui.utils import post_redisplay


class CameraInteractor:

    SPHERE = 'sphere'
    FREELOOK = 'freelook'
    PAN = 'pan'

    camera_type = None

    def __init__(self, camera=Camera(), reset_mv=True):

        self.camera = camera
        self._distance = 0
        self._forward = 0
        self._strafe = 0
        self._shift_x = 0
        self._shift_y = 0
        self._angle_x = 0
        self._angle_y = 0
        self._friction = 200
        self.default_matrix = None
        self.reset_position(reset_mv=reset_mv)

    def key_down(self, key):
        pass  # implemented by subclasses

    def key_up(self, key):
        pass  # implemented by subclasses

    def mouse_motion(self, dx, dy, shift, alt, ctrl):
        pass  # implemented by subclasses

    def mouse_wheel(self, value, delta, shift, alt, ctrl):
        pass  # implemented by subclasses

    def refresh_position(self):
        pass  # implemented by subclasses

    def reset_position(self, reset_mv=True):
        pass  # implemented by subclasses


class SphereInteractor(CameraInteractor):

    def __init__(self, camera, reset_mv=True):
        self.camera_type = CameraInteractor.SPHERE
        super().__init__(camera, reset_mv)

    def mouse_motion(self, dx, dy, shift, alt, ctrl):
        friction = self._friction
        center_dist = self.camera.distance_to_point(self.camera.scene.bounding_box.center)
        if shift:
            self._distance = self._distance + dy / friction * center_dist
        elif ctrl:
            self._shift_x = self._shift_x + dx * center_dist / friction
            self._shift_y = self._shift_y - dy * center_dist / friction
        else:
            self._angle_x = self._angle_x + dx / friction
            self._angle_y = self._angle_y - dy / friction
        self.refresh_position()

    def mouse_wheel(self, value, delta, shift, alt, ctrl):
        bbox = self.camera.scene.bounding_box
        diameter = bbox.diameter
        orig_dist = bbox.max_z + diameter
        curr_dist = self.camera.distance_to_point(bbox.center)
        dist_ratio = 1 - (orig_dist - curr_dist) / orig_dist
        if dist_ratio < 0:
            dist_ratio = -math.log(-dist_ratio)
        scene_size_mult = 0.8 * diameter / 2
        zoom_amt = value / delta * scene_size_mult * dist_ratio
        if value < 0 and zoom_amt <= 0:
            zoom_amt = zoom_amt - 1
        if shift is True:
            zoom_amt = zoom_amt * 2
        elif ctrl is True:
            zoom_amt = zoom_amt * 0.25

        self._distance = self._distance + zoom_amt
        self.refresh_position()

    def refresh_position(self):
        center = self.camera.scene.bounding_box.center
        dummy_cam = Camera()
        dummy_cam.matrix = self.default_matrix
        z_shift = dummy_cam.distance_to_point(center)
        self.camera.matrix = Matrix44.from_translation([self._shift_x, self._shift_y, self._distance]) * \
                             Matrix44.from_translation([0, 0, -z_shift]) * \
                             Matrix44.from_x_rotation(-self._angle_y) * \
                             Matrix44.from_y_rotation(-self._angle_x) * \
                             Matrix44.from_translation([0, 0, z_shift]) * \
                             self.default_matrix

        post_redisplay()

    def reset_position(self, reset_mv=True):
        if reset_mv:
            self.camera.matrix = Matrix44.identity(dtype=numpy.float32)
            bbox = self.camera.scene.bounding_box
            center = bbox.center
            eye = Vector3([center.x, center.y, bbox.max_z + bbox.diameter])
            up = Vector3([0, 1, 0])
            self.camera.look_at(eye, center, up)
        self.default_matrix = self.camera.matrix
        self._distance = 0
        self._forward = 0
        self._strafe = 0
        self._shift_x = 0
        self._shift_y = 0
        self._angle_x = 0
        self._angle_y = 0
        self.refresh_position()


class FreelookInteractor(CameraInteractor):

    def __init__(self, camera, reset_mv=True):
        self.camera_type = CameraInteractor.FREELOOK
        super().__init__(camera, reset_mv)

    def mouse_motion(self, dx, dy, shift, alt, ctrl):
        friction = 5.0
        self._forward = 0.0
        self._strafe = 0.0
        self._angle_x = self._angle_x + dy / friction
        self._angle_y = self._angle_y + dx / friction
        self.refresh_position()

    def key_down(self, key):
        self._forward = 0.0
        self._strafe = 0.0
        friction = self.camera.scene.bounding_box.diameter / 500.0
        if key == "W":
            self._forward = self._forward - friction
        elif key == "S":
            self._forward = self._forward + friction
        elif key == "A":
            self._strafe = self._strafe - friction
        elif key == "D":
            self._strafe = self._strafe + friction
        self.refresh_position()

    def refresh_position(self):
        self.camera.move_relative(Vector3([self._strafe, 0.0, self._forward]))
        pos = self.camera.get_position()
        self.camera.matrix = self.default_matrix * Matrix44.from_y_rotation(self._angle_y) * \
                             Matrix44.from_x_rotation(self._angle_x)
        self.camera.set_position(pos)
        post_redisplay()

    def reset_position(self, reset_mv=True):
        self._strafe = 0.0
        self._forward = 0.0
        self._angle_y = self._angle_x = 0.0
        if reset_mv:
            self.camera.matrix = Matrix44.identity(dtype=numpy.float32)
        self.default_matrix = self.camera.matrix
        self.refresh_position()


class PanInteractor(SphereInteractor):

    def __init__(self, camera, reset_mv=True):
        super().__init__(camera, reset_mv)
        self.camera_type = CameraInteractor.PAN

    def mouse_motion(self, dx, dy, shift, alt, ctrl):
        dist = self.camera.distance_to_point(self.camera.scene.bounding_box.center) / self._friction
        self._shift_x = self._shift_x + dx * dist
        self._shift_y = self._shift_y - dy * dist
        self.refresh_position()
