import numpy
from OpenGL.GL import *


def map_buffer(target, type, access, size):
    fn = ctypes.pythonapi.PyMemoryView_FromMemory
    fn.restype = ctypes.py_object

    ptr = glMapBuffer(target, access)
    buffer = func(ctypes.c_void_p(ptr), size, ctypes.pythonapi.PyBUF_WRITE)

    return numpy.frombuffer(buffer, type)
