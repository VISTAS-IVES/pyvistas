import os
import sys
from distutils.extension import Extension

from Cython.Build import cythonize
from cx_Freeze import setup, Executable

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))

os.environ['TCL_LIBRARY'] = r'C:\Python35\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'C:\Python35\tcl\tk8.6'

build_options = dict(
    packages=['asyncio', 'OpenGL', 'tkinter', 'numpy', 'pyproj', 'vistas'],
    excludes=[],
    include_files=[('../plugins', 'plugins'), ('../resources', 'resources')],
    constants='VISTAS_PROFILE="deploy"'
)

base = 'Win32GUI' if sys.platform=='win32' else None

executables = [
    Executable(
        'main.py', base=base, targetName='VISTAS.exe', icon='../resources/images/vistas.ico'
    )
]

extensions = [
    Extension(
        'vistas.core.encoders.wmv._wmv',
        sources=['vistas/core/encoders/wmv/_wmv.pyx'],
        libraries=['Mfuuid', 'Mfplat', 'Mfreadwrite'],
        language='c++'
    )
]

setup(
    name='VISTAS',
    version='1.0',
    description='VISTAS',
    options=dict(build_exe=build_options),
    executables=executables,
    ext_modules=cythonize(extensions)
)
