import os
from PIL import Image

import imageio
import numpy
import requests
from imageio.core.util import appdata_dir
from imageio.plugins.ffmpeg import FNAME_PER_PLATFORM, get_platform

from vistas.core.encoders.interface import VideoEncoder
from vistas.core.task import Task
from vistas.core.threading import Thread

FFMPEG_ROOT_URL = 'https://github.com/imageio/imageio-binaries/raw/master/ffmpeg/'


class ImageIOVideoEncoder(VideoEncoder):
    """ A video encoder which exports videos utilizing the imageio library. """

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


class DownloadFFMpegThread(Thread):
    """
    A worker thread that downloads the ffmpeg libraries to the default imageio appdata directory.
    """

    def run(self):
        file = FNAME_PER_PLATFORM[get_platform()]
        path = os.path.join(appdata_dir('imageio'), 'ffmpeg', file)

        if os.path.exists(path):
            return

        task = Task("Downloading FFmpeg")
        task.status = task.RUNNING

        try:
            ffmpeg_dir = os.path.dirname(path)
            if not os.path.exists(ffmpeg_dir):
                os.makedirs(ffmpeg_dir)

            with requests.get(FFMPEG_ROOT_URL + file, stream=True) as r:
                if r.headers.get('content-length'):
                    task.target = int(r.headers['content-length'])
                else:
                    task.status = task.INDETERMINATE

                with open(path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=None):
                        f.write(chunk)
                        task.inc_progress(len(chunk))
        finally:
            task.status = task.COMPLETE


