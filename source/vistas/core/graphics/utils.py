from _testbuffer import PyBUF_WRITE

import numpy
from OpenGL.GL import *


def map_buffer(target, type, access, size):
    fn = ctypes.pythonapi.PyMemoryView_FromMemory
    fn.restype = ctypes.py_object

    ptr = glMapBuffer(target, access)
    buffer = fn(ctypes.c_void_p(ptr), size, PyBUF_WRITE)

    return numpy.frombuffer(buffer, type)
