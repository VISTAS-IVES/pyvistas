from _testbuffer import PyBUF_WRITE

import numpy
from OpenGL.GL import *


def map_buffer(target, type, access, size):
    """ Maps an OpenGL buffer back to a numpy array. """
    fn = ctypes.pythonapi.PyMemoryView_FromMemory
    fn.restype = ctypes.py_object

    ptr = glMapBuffer(target, access)
    buffer = fn(ctypes.c_void_p(ptr), size, PyBUF_WRITE)

    return numpy.frombuffer(buffer, type)
