import os
import sys

from cx_Freeze import setup, Executable

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))

if 'TCL_LIBRARY' not in os.environ:
    os.environ['TCL_LIBRARY'] = r'C:\Python35\tcl\tcl8.6'
if 'TK_LIBRARY' not in os.environ:
    os.environ['TK_LIBRARY'] = r'C:\Python35\tcl\tk8.6'

build_options = dict(
    packages=[
        'asyncio', 'OpenGL', 'tkinter', 'numpy', 'pyproj', 'vistas', 'netCDF4', 'netcdftime', 'fiona', 'rasterio',
        'requests', 'idna', 'rasterstats', 'clover', 'sklearn', 'scipy', 'scipy.spatial.ckdtree'
    ],
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

setup(
    name='VISTAS',
    version='1.19.0',
    description='VISTAS',
    options=dict(build_exe=build_options),
    executables=executables
)
