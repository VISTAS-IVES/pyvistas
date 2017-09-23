import os
import platform
import shutil

import cx_Freeze
from cx_Freeze import setup, Executable

import vistas

version = vistas.__version__

macos = platform.uname().system == 'Darwin'
SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))

cmdclass = {}

if macos:
    build_options = dict(
        packages=[
            'numpy', 'asyncio', 'idna', 'OpenGL', 'matplotlib', 'vistas', 'rasterio', 'netCDF4', 'netcdftime', 'fiona', 'rasterstats', 'clover'
        ],
        excludes=['tcl', 'ttk', 'tkinter', 'Tkinter'],
        include_files=[],
        constants='VISTAS_PROFILE="deploy"'
    )

    executables = [
        Executable('main.py', base=None, targetName='VISTAS')
    ]


    class bdist_mac(cx_Freeze.bdist_mac):
        def copy_assets(self):
            resources_dir = os.path.join(self.resourcesDir, 'resources')
            if os.path.exists(resources_dir):
                shutil.rmtree(resources_dir)
            shutil.copytree(os.path.join(SOURCE_DIR, '..', 'resources'), resources_dir)

            plugins_dir = os.path.join(self.resourcesDir, 'plugins')
            if os.path.exists(plugins_dir):
                shutil.rmtree(plugins_dir)
            shutil.copytree(os.path.join(SOURCE_DIR, '..', 'plugins'), plugins_dir)

        def run(self):
            super().run()
            self.copy_assets()

    options = dict(
        build_exe=build_options,
        bdist_mac=dict(
            iconfile='../resources/images/VISTAS.icns', bundle_name='VISTAS', #codesign_identity='VISTAS Release'
        ),
        bdist_dmg=dict(volume_label='VISTAS {}'.format(version), applications_shortcut=True)
    )

    cmdclass = dict(bdist_mac=bdist_mac)
else:
    build_options = dict(
        packages=[
            'asyncio', 'OpenGL', 'tkinter', 'numpy', 'pyproj', 'vistas', 'netCDF4', 'netcdftime', 'fiona', 'rasterio',
            'requests', 'idna', 'rasterstats', 'clover', 'sklearn', 'scipy', 'scipy.spatial.ckdtree'
        ],
        excludes=[],
        include_files=[('../plugins', 'plugins'), ('../resources', 'resources')],
        constants='VISTAS_PROFILE="deploy"'
    )

    executables = [
        Executable(
            'main.py', base='Win32GUI', targetName='VISTAS.exe', icon='../resources/images/vistas.ico'
        )
    ]

    options = dict(
        build_exe=build_options
    )


setup(
    name='VISTAS',
    version='1.18.0',
    description='VISTAS',
    options=options,
    executables=executables,
    cmdclass=cmdclass
)
