import ctypes
from _testbuffer import PyBUF_WRITE
from ctypes.util import find_library

import numpy


cdef extern from "<mfapi.h>":
    unsigned long FCC(unsigned int)
    int MFSetAttributeSize(void*, const GUID&, unsigned int, unsigned int)
    int MFSetAttributeRatio(void*, const GUID&, unsigned int, unsigned int)


cdef extern from "<guiddef.h>":
    ctypedef struct GUID:
        unsigned long Data1
        unsigned short Data2
        unsigned short Data3
        unsigned char Data4[8]


cdef extern from "Mfidl.h":
    cdef cppclass IMFMediaType:
        int SetGUID(const GUID&, const GUID&)
        int SetUINT32(const GUID&, unsigned int)
        unsigned long Release()

    cdef cppclass IMFSample:
        int AddBuffer(IMFMediaBuffer*)
        int SetSampleTime(long long)
        int SetSampleDuration(long long)
        unsigned long Release()

    cdef cppclass IMFMediaBuffer:
        int Lock(unsigned char**, unsigned long*, unsigned long*)
        int Unlock()
        int SetCurrentLength(unsigned long)
        int GetMaxLength(unsigned long*)
        unsigned long Release()


cdef extern from "Mfreadwrite.h":
    cdef cppclass IMFSinkWriter:
        int AddStream(void*, unsigned long*)
        int SetInputMediaType(unsigned long, void*, void*)
        int BeginWriting()
        int WriteSample(unsigned long, IMFSample*)
        unsigned long Finalize()
        unsigned long AddRef()
        unsigned long Release()


plat_lib = ctypes.cdll.LoadLibrary(find_library('Mfplat'))
readwrite_lib = ctypes.cdll.LoadLibrary(find_library('mfreadwrite'))


def raise_on_error(hr):
    if hr < 0:
        raise MFException(hr)
    return hr


class MFException(Exception):
    def __init__(self, code):
        self.code = code


cdef class Py_IMFMediaType:
    cdef IMFMediaType *c_obj

    def __cinit__(self):
        obj = ctypes.c_void_p()
        raise_on_error(plat_lib.MFCreateMediaType(ctypes.byref(obj)))
        self.c_obj = <IMFMediaType*> <size_t> obj.value

    def release(self):
        return raise_on_error(self.c_obj.Release())

    def set_guid(self, PyGUID key, PyGUID value):
        return raise_on_error(self.c_obj.SetGUID(key.c_guid, value.c_guid))

    def set_uint32(self, PyGUID key, int value):
        return raise_on_error(self.c_obj.SetUINT32(key.c_guid, value))

    def set_attribute_size(self, PyGUID key, int width, int height):
        return raise_on_error(MFSetAttributeSize(self.c_obj, key.c_guid, width, height))

    def set_attribute_ratio(self, PyGUID key, int numerator, int denominator):
        return raise_on_error(MFSetAttributeRatio(self.c_obj, key.c_guid, numerator, denominator))


cdef class Py_IMFSinkWritier:
    cdef IMFSinkWriter *c_obj

    def __cinit__(self, object path):
        obj = ctypes.c_void_p()
        raise_on_error(readwrite_lib.MFCreateSinkWriterFromURL(path, None, None, ctypes.byref(obj)))
        self.c_obj = <IMFSinkWriter*> <size_t> obj.value

    def add_stream(self, Py_IMFMediaType target_media_type):
        cdef unsigned long stream_index
        raise_on_error(self.c_obj.AddStream(target_media_type.c_obj, &stream_index))
        return stream_index

    def set_input_media_type(self, unsigned long stream_index, Py_IMFMediaType media_type):
        return raise_on_error(self.c_obj.SetInputMediaType(stream_index, media_type.c_obj, NULL))

    def begin_writing(self):
        return raise_on_error(self.c_obj.BeginWriting())

    def write_sample(self, unsigned long stream_index, Py_IMFSample sample):
        return raise_on_error(self.c_obj.WriteSample(stream_index, sample.c_obj))

    def finalize(self):
        return raise_on_error(self.c_obj.Finalize())

    def add_ref(self):
        return raise_on_error(self.c_obj.AddRef())

    def release(self):
        return raise_on_error(self.c_obj.Release())


cdef class Py_IMFSample:
    cdef IMFSample *c_obj

    def __cinit__(self):
        obj = ctypes.c_void_p()
        raise_on_error(plat_lib.MFCreateSample(ctypes.byref(obj)))
        self.c_obj = <IMFSample*> <size_t> obj.value

    def add_buffer(self, Py_IMFMediaBuffer buffer):
        raise_on_error(self.c_obj.AddBuffer(buffer.c_obj))

    def set_sample_time(self, long long sample_time):
        raise_on_error(self.c_obj.SetSampleTime(sample_time))

    def set_sample_duration(self, long long duration):
        raise_on_error(self.c_obj.SetSampleDuration(duration))

    def release(self):
        return raise_on_error(self.c_obj.Release())


cdef class Py_IMFMediaBuffer:
    cdef IMFMediaBuffer *c_obj

    def __cinit__(self, max_length):
        obj = ctypes.c_void_p()
        raise_on_error(plat_lib.MFCreateMemoryBuffer(max_length, ctypes.byref(obj)))
        self.c_obj = <IMFMediaBuffer*> <size_t> obj.value

    def lock(self):
        cdef unsigned char *data
        cdef unsigned long size

        raise_on_error(self.c_obj.GetMaxLength(&size))
        raise_on_error(self.c_obj.Lock(&data, NULL, NULL))

        fn = ctypes.pythonapi.PyMemoryView_FromMemory
        fn.restype = ctypes.py_object

        buffer = fn(ctypes.c_void_p(<int>data), size, PyBUF_WRITE)
        return numpy.frombuffer(buffer, 'uint8')

    def unlock(self):
        return self.c_obj.Unlock()

    def set_current_length(self, unsigned long size):
        self.c_obj.SetCurrentLength(size)

    def release(self):
        return raise_on_error(self.c_obj.Release())


cdef class PyGUID:
    cdef GUID c_guid

    def __cinit__(self, l, w1, w2, b1, b2, b3, b4, b5, b6, b7, b8):
        self.c_guid.Data1 = l
        self.c_guid.Data2 = w1
        self.c_guid.Data3 = w2
        self.c_guid.Data4[:] = [b1, b2, b3, b4, b5, b6, b7, b8]


cdef multi_literal(const char[4] s):
    """ Emulate the msvc compiler handling of multi-character literals """

    return s[0]<<24 | s[1]<<16 | s[2]<<8 | s[3]

MF_MT_MAJOR_TYPE = PyGUID(0x48eba18e, 0xf8c9, 0x4687, 0xbf, 0x11, 0x0a, 0x74, 0xc9, 0xf9, 0x6a, 0x8f)
MF_MT_SUBTYPE = PyGUID(0xf7e34c9a, 0x42e8, 0x4714, 0xb7, 0x4b, 0xcb, 0x29, 0xd7, 0x2c, 0x35, 0xe5)
MF_MT_AVG_BITRATE = PyGUID(0x20332624, 0xfb0d, 0x4d9e, 0xbd, 0x0d, 0xcb, 0xf6, 0x78, 0x6c, 0x10, 0x2e)
MF_MT_INTERLACE_MODE = PyGUID(0xe2724bb8, 0xe676, 0x4806, 0xb4, 0xb2, 0xa8, 0xd6, 0xef, 0xb4, 0x4c, 0xcd)
MF_MT_FRAME_SIZE = PyGUID(0x1652c33d, 0xd6b2, 0x4012, 0xb8, 0x34, 0x72, 0x03, 0x08, 0x49, 0xa3, 0x7d)
MF_MT_FRAME_RATE = PyGUID(0xc459a2e8, 0x3d2c, 0x4e44, 0xb1, 0x32, 0xfe, 0xe5, 0x15, 0x6c, 0x7b, 0xb0)
MF_MT_PIXEL_ASPECT_RATIO = PyGUID(0xc6376a1e, 0x8d0a, 0x4027, 0xbe, 0x45, 0x6d, 0x9a, 0x0a, 0xd3, 0x9b, 0xb6)
MFMediaType_Video = PyGUID(0x73646976, 0x0000, 0x0010, 0x80, 0x00, 0x00, 0xAA, 0x00, 0x38, 0x9B, 0x71)
MFVideoFormat_RGB32 = PyGUID(22, 0x0000, 0x0010, 0x80, 0x00, 0x00, 0xaa, 0x00, 0x38, 0x9b, 0x71)
MFVideoFormat_WMV3 = PyGUID(FCC(multi_literal('WMV3')), 0x0000, 0x0010, 0x80, 0x00, 0x00, 0xaa, 0x00, 0x38, 0x9b, 0x71)
