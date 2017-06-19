import os

from PIL import Image

from vistas.core.encoders.interface import VideoEncoder


class PNGEncoder(VideoEncoder):
    """ A "video" encoder which simple exports each frame to a still image file """

    def __init__(self):
        self.frame_number = None
        self.export_directory = None

    def open(self, path, width, height):
        self.frame_number = 1
        if os.path.isdir(path):
            self.export_directory = path
        else:
            self.export_directory = os.path.dirname(path)

    def write_frame(self, bitmap: Image, duration):
        bitmap.save(os.path.join(self.export_directory, 'Frame {}.png'.format(self.frame_number)))
        self.frame_number += 1

    def finalize(self):
        pass

    def set_framerate(self, fps):
        pass

    def is_ok(self):
        return self.export_directory is not None and os.path.exists(self.export_directory)
