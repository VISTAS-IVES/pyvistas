import os

import wx

from vistas.core.utils import get_platform

try:
    import BUILD_CONSTANTS
except ImportError:
    BUILD_CONSTANTS = None


def get_assets_dir():
    """ Return the current asset directory. """

    profile = getattr(BUILD_CONSTANTS, 'VISTAS_PROFILE', 'dev')

    if get_platform() == 'windows':
        return os.path.join(os.getcwd(), '' if profile == 'deploy' else '..')
    else:
        if profile == 'dev':
            return os.path.join(os.path.dirname(wx.StandardPaths.Get().ExecutablePath), '..')
        else:
            return os.path.join(os.path.dirname(wx.StandardPaths.Get().ExecutablePath), '..', 'Resources')


def get_builtin_plugins_directory():
    """ Return the current builtin plugins directory. """

    if get_platform() == 'windows':
        return os.path.join(get_assets_dir(), 'plugins')
    else:
        return os.path.join(get_assets_dir(), 'plugins')


def get_resources_directory():
    """ Return the current resources directory. """

    if get_platform() == 'windows':
        return os.path.join(get_assets_dir(), 'resources')
    else:
        return os.path.join(os.path.dirname(wx.StandardPaths.Get().ExecutablePath), '..', 'resources')


def get_builtin_shader(path):
    return os.path.join(get_resources_directory(), 'shaders', path)


def get_config_dir():
    if get_platform() == 'macos':
        return os.path.join(wx.StandardPaths.Get().UserLocalDataDir, 'VISTAS')
    else:
        return os.path.join(wx.StandardPaths.Get().UserConfigDir, 'VISTAS')


def get_resource_bitmap(name):
    """ Return the named image file as a wx.Bitmap. """

    return wx.Image(os.path.join(get_resources_directory(), 'images', name)).ConvertToBitmap()


def get_icon(name):
    """ Return the named icon file as a wx.Icon. """

    return wx.Icon(wx.IconLocation(os.path.join(get_resources_directory(), 'images', name)))
