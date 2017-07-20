import os

import imageio
import numpy
from PIL import Image
from imageio.plugins.ffmpeg import FNAME_PER_PLATFORM, get_platform

from vistas.core.encoders.interface import VideoEncoder
from vistas.core.paths import get_resources_directory

ffmpeg_exe = os.path.abspath(os.path.join(get_resources_directory(), 'ffmpeg', FNAME_PER_PLATFORM[get_platform()]))
os.environ.setdefault('IMAGEIO_FFMPEG_EXE', ffmpeg_exe)


class ImageIOVideoEncoder(VideoEncoder):

    def __init__(self):
        self._fps = 30
        self.writer = None
        self.width = 800
        self.height = 600
        self.quality = 8

    @property
    def fps(self):
        return self._fps

    @fps.setter
    def fps(self, fps):
        self._fps = int(fps) if fps > 1 else 1

    def open(self, path, width, height):

        self.width = width
        self.height = height

        macro_block = 16
        rem = self.width / macro_block % macro_block
        if rem != 0:
            self.width = round(self.width / macro_block) * macro_block

        rem = self.height / macro_block % macro_block
        if rem != 0:
            self.height = round(self.height / macro_block) * macro_block

        if os.path.exists(path):
            os.remove(path)

        self.writer = imageio.get_writer(path, fps=self.fps, quality=self.quality)

    def write_frame(self, bitmap: Image, duration):
        if bitmap.size != (self.width, self.height):
            bitmap = bitmap.resize((self.width, self.height))
        self.writer.append_data(numpy.array(bitmap))

    def finalize(self):
        self.writer.close()

    def is_ok(self):
        return not self.writer.closed
