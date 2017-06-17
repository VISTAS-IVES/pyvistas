import logging
import os
from ctypes import cdll, byref, c_ulong
from ctypes.util import find_library

import numpy
from PIL import Image

from vistas.core.encoders.interface import VideoEncoder
from vistas.core.encoders.wmv._wmv import Py_IMFMediaType, MF_MT_MAJOR_TYPE, MFMediaType_Video, MF_MT_SUBTYPE
from vistas.core.encoders.wmv._wmv import MFVideoFormat_WMV3, MF_MT_AVG_BITRATE, MF_MT_INTERLACE_MODE, MF_MT_FRAME_SIZE
from vistas.core.encoders.wmv._wmv import MF_MT_PIXEL_ASPECT_RATIO, MFException, Py_IMFSinkWritier, raise_on_error
from vistas.core.encoders.wmv._wmv import Py_IMFMediaBuffer, Py_IMFSample, MF_MT_FRAME_RATE, MFVideoFormat_RGB32
from vistas.core.utils import get_platform

logger = logging.getLogger(__name__)

BIT_RATE = 800000
WIDTH_BASE = 40
HEIGHT_BASE = 30

# Microsoft library enumerations
COINIT_APARTMENTTHREADED = 0x2  # objbase.h
MF_VERSION = 0x0002 << 16 | 0x0070  # mfapi.h


class WMVEncoder(VideoEncoder):
    def __init__(self):
        if get_platform() != 'windows':
            raise OSError('WMV encoder supported only on Windows')

        self.sink_writer = None
        self.stream_index = None
        self.ok = False
        self.current_frame = 0
        self.width = 0
        self.height = 0
        self._fps = 30

        self.ole_lib = cdll.LoadLibrary(find_library('Ole32'))
        self.plat_lib = cdll.LoadLibrary(find_library('Mfplat'))

    @property
    def fps(self):
        return self._fps

    @fps.setter
    def fps(self, value):
        self._fps = int(value) if value > 1 else 1

    def fit_dimensions(self, width, height):
        if width % WIDTH_BASE != 0:
            width -= width % WIDTH_BASE
        if height % HEIGHT_BASE != 0:
            height -= height % HEIGHT_BASE

        return width, height

    def get_options(self):
        return []

    def open(self, path, width, height):
        self.width, self.height = self.fit_dimensions(width, height)

        media_type_out = media_type_in = None

        try:
            raise_on_error(self.ole_lib.CoInitializeEx(None, COINIT_APARTMENTTHREADED))
            raise_on_error(self.plat_lib.MFStartup(MF_VERSION))

            self.sink_writer = Py_IMFSinkWritier(os.path.abspath(path))

            media_type_out = Py_IMFMediaType()
            media_type_out.set_guid(MF_MT_MAJOR_TYPE, MFMediaType_Video)
            media_type_out.set_guid(MF_MT_SUBTYPE, MFVideoFormat_WMV3)
            media_type_out.set_uint32(MF_MT_AVG_BITRATE, BIT_RATE)
            media_type_out.set_uint32(MF_MT_INTERLACE_MODE, 2)  # MFVideoInterlace_Progressive
            media_type_out.set_attribute_size(MF_MT_FRAME_SIZE, self.width, self.height)
            media_type_out.set_attribute_ratio(MF_MT_FRAME_RATE, self.fps, 1)
            media_type_out.set_attribute_ratio(MF_MT_PIXEL_ASPECT_RATIO, 1, 1)
            self.stream_index = self.sink_writer.add_stream(media_type_out)

            media_type_in = Py_IMFMediaType()
            media_type_in.set_guid(MF_MT_MAJOR_TYPE, MFMediaType_Video)
            media_type_in.set_guid(MF_MT_SUBTYPE, MFVideoFormat_RGB32)
            media_type_in.set_uint32(MF_MT_INTERLACE_MODE, 2)  # MFVideoInterlace_Progressive
            media_type_in.set_attribute_size(MF_MT_FRAME_SIZE, self.width, self.height)
            media_type_in.set_attribute_ratio(MF_MT_FRAME_RATE, self.fps, 1)
            media_type_in.set_attribute_ratio(MF_MT_PIXEL_ASPECT_RATIO, 1, 1)
            self.sink_writer.set_input_media_type(self.stream_index, media_type_in)

            self.sink_writer.begin_writing()
            self.sink_writer.add_ref()
            self.current_frame = 0
            self.ok = True

        except MFException as e:
            logger.exception('Opening file for streaming failed with code {}'.format(e.code))
            self.ok = False

        finally:
            if media_type_out is not None:
                media_type_out.release()

            if media_type_in is not None:
                media_type_in.release()

    def write_frame(self, bitmap: Image, duration):
        buffer_size = self.width * self.height * 4

        sample = buffer = None

        try:
            sample_duration = c_ulong()
            raise_on_error(self.plat_lib.MFFrameRateToAverageTimePerFrame(self.fps, 1, byref(sample_duration)))
            sample_duration = sample_duration.value * duration * self.fps

            buffer = Py_IMFMediaBuffer(buffer_size)
            data = buffer.lock()

            bitmap = bitmap.resize((self.width, self.height))
            arr = numpy.asarray(bitmap)
            data[:] = arr.reshape(-1, 4)[:, [2, 1, 0, 3]].ravel()  # RGBA -> BGRA

            buffer.unlock()
            buffer.set_current_length(buffer_size)

            sample = Py_IMFSample()
            sample.add_buffer(buffer)
            sample.set_sample_time(self.current_frame)
            sample.set_sample_duration(sample_duration)

            self.current_frame += sample_duration

            self.sink_writer.write_sample(self.stream_index, sample)

            self.ok = True

        except MFException as e:
            logger.exception('Opening file for streaming failed with code {}'.format(e.code))
            self.ok = False

        finally:
            if sample is not None:
                sample.release()

            if buffer is not None:
                buffer.release()

    def finalize(self):
        if self.sink_writer is not None:
            self.sink_writer.finalize()
            self.sink_writer.release()

        raise_on_error(self.plat_lib.MFShutdown())
        self.ole_lib.CoUninitialize()

    def is_ok(self):
        return self.ok
