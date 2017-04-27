from vistas.core.graphics.vector import Vector
from vistas.core.graphics.camera import Camera
from vistas.core.math import catmull_rom_splines

from math import floor

class FlythroughPoint:
    def __init__(self, position=Vector(0, 0, 0), direction=Vector(0, 0, 0), up=Vector(0, 1, 0)):
        self.position = position
        self.direction = direction
        self.up = up

class Flythrough:
    def __init__(self, camera=None, fps=30, length=60, name='', ):
        if camera is None:
            camera = Camera()

        self.camera = camera
        self._fps = fps
        self._length = length
        self.name = name

        self._keyframes = {}

    def __del__(self):
        pass  # Todo

    def _rescale_keyframes(self, fps=None, length=None):
        rescaled_keyframes = {}

        if fps is None:
            fps = self._fps
        if length is None:
            length = self._length

        new_max = fps * length
        old_max = self.num_keyframes

        if new_max != old_max:
            if new_max < old_max:
                for p_idx, p in enumerate(self._keyframes):
                    rescaled_keyframes[int(floor(p_idx * new_max) / old_max)] = p
            elif new_max > old_max:
                for p_idx, p in reversed(enumerate(self._keyframes)):
                    rescaled_keyframes[int(floor(p_idx * new_max) / old_max)] = p

            self._keyframes = rescaled_keyframes

            # Appease delayed setters
            self._fps = fps
            self._length = length

    @property
    def fps(self):
        return self._fps

    @fps.setter
    def fps(self, value):
        self._rescale_keyframes(fps=value)

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, value):
        self._rescale_keyframes(length=value)

    @property
    def num_keyframes(self):
        return self._fps * self._length

    def update_camera_to_keyframe(self, index: int):
        p = self.get_keyframe_at_index(index)

        self.camera.set_position(p.position)
        self.camera.set_up_vector(p.up)
        self.camera.set_point_of_interest(p.direction + p.position)

        # Todo - UIPostRedisplay?

    def add_keyframe(self, index: int, point=None):
        if point is None:
            point = FlythroughPoint(self.camera.get_position(),
                                    self.camera.get_direction(),
                                    self.camera.get_up_vector())
        self._keyframes[index] = point

    def remove_keyframe(self, index: int):
        if self.is_keyframe(index):
            self._keyframes.pop(index)

    def get_keyframe_at_index(self, index: int):
        current_point = FlythroughPoint(self.camera.get_position(),
                                        self.camera.get_direction(),
                                        self.camera.get_up_vector())
        if len(self._keyframes) < 2:
            return current_point
        elif self.is_keyframe(index):
            return self._keyframes[index]
        else:
            return self._get_keyframe_at_index(index, current_point)

    def _get_keyframe_at_index(self, index: int, current_point) -> FlythroughPoint:

        # find the keyframes directly above and below the requested indices
        low_index = -1
        num_keyframes = self.num_keyframes
        high_index = num_keyframes + 1
        low_value = FlythroughPoint()
        lower_value = FlythroughPoint()
        high_value = FlythroughPoint()
        higher_value = None

        for p_idx, p in enumerate(self._keyframes):

            # find the low keyframe and the one before if there is one
            if low_index < p_idx < index:
                if 0 <= low_index < index:
                    lower_value = self._keyframes[low_index]
                else:
                    lower_value = FlythroughPoint()
                low_index = p_idx
                low_value = p

            # find the high keyframe and the one after if there is one
            if index < p_idx < high_index:
                if num_keyframes >= high_index > index:
                    higher_value = self._keyframes[high_index]
                high_index = p_idx
                high_value = p

        if low_index < 0 and high_index > num_keyframes:
            return current_point
        elif low_index < 0:
            return high_value
        elif high_index > num_keyframes:
            return low_value
        else:
            t = (index - low_index) / (high_index - low_index)
            if higher_value is None:
                higher_value = FlythroughPoint(
                    high_value.position + high_value.position - low_value.position,
                    high_value.direction + high_value.direction - low_value.direction,
                    high_value.up + high_value.up + low_value.up
                )

            return FlythroughPoint(
                catmull_rom_splines(
                    lower_value.position, low_value.position, high_value.position, higher_value.position, t
                ),
                catmull_rom_splines(
                    lower_value.direction, low_value.direction, high_value.direction, higher_value.direction, t
                ),
                (low_value.up * (1.0 - t)) + (high_value.up * t)
            )

    def is_keyframe(self, idx):
        return idx in self._keyframes.keys()

    @property
    def keyframes(self):
        return self._keyframes

    @property
    def keyframe_indices(self):
        return list(self._keyframes.keys())

    def remove_all_keyframes(self):
        self._keyframes = {}
