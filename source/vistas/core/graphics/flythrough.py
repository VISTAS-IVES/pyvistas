from pyrr import Vector3
from vistas.core.graphics.camera import Camera
from vistas.core.math import catmull_rom_splines, cubic_interpolation
from vistas.ui.utils import post_redisplay

from math import floor


class FlythroughPoint:
    def __init__(self, position=Vector3(), direction=Vector3(), up=Vector3([0, 1, 0])):
        self.position = position
        self.direction = direction
        self.up = up


class Flythrough:
    def __init__(self, scene, fps=30, length=60):

        self.camera = Camera(scene=scene)
        self._fps = fps
        self._length = length

        self._keyframes = {}

    def __del__(self):
        post_redisplay()

    def _rescale_keyframes(self, fps=None, length=None):

        if fps is None:
            fps = self._fps
        if length is None:
            length = self._length

        new_max = fps * length
        old_max = self.num_keyframes

        if new_max != old_max:
            if new_max < old_max:
                items = self._keyframes.items()
            else:
                items = reversed(list(self._keyframes.items()))
            self._keyframes = {int(floor(p_idx * new_max) / old_max): p for p_idx, p in items}

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
        self.camera.look_at(p.position, p.position + p.direction, p.up)
        post_redisplay()

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

        # Determine keyframes directly above and below the requested index
        indices = sorted(list(self._keyframes.keys()))

        low_index = indices[0] if index < indices[0] else [x for x in indices if x < index][-1]
        low_value = self._keyframes[low_index]
        high_index = indices[-1] if index > indices[-1] else [x for x in indices if x > index][0]
        high_value = self._keyframes[high_index]

        # Catch if we're below the lowest recorded keyframe
        if index < indices[0]:
            return self._keyframes[indices[0]]

        # Catch if we're above the highest recorded keyframe
        if index > indices[-1]:
            return self._keyframes[indices[-1]]

        # Now get keyframes below low_value and above high_value, if they exist
        lower_index = indices.index(low_index) - 1
        if lower_index < 0:
            lower_value = FlythroughPoint()
        else:
            lower_value = self._keyframes[indices[lower_index]]

        higher_index = indices.index(high_index) + 1
        if higher_index >= len(indices):
            higher_value = FlythroughPoint(
                position=high_value.position + high_value.position - low_value.position,
                direction=high_value.direction + high_value.direction - low_value.direction,
                up=high_value.up + high_value.up - low_value.up,
            )
        else:
            higher_value = self._keyframes[indices[higher_index]]

        t = (index - low_index) / (high_index - low_index)

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
