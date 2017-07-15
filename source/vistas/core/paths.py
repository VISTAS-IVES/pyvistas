import os

import wx

from vistas.core.utils import get_platform

try:
    import BUILD_CONSTANTS
except ImportError:
    BUILD_CONSTANTS = None


def get_assets_dir():
    profile = getattr(BUILD_CONSTANTS, 'VISTAS_PROFILE', 'dev')

    return '' if profile == 'deploy' else '..'


def get_builtin_plugins_directory():
    if get_platform() == 'windows':
        return os.path.join(os.getcwd(), get_assets_dir(), 'plugins')
    else:
        return os.path.join(os.path.dirname(wx.StandardPaths.Get().ExecutablePath), '..', 'plugins')


def get_resources_directory():
    if get_platform() == 'windows':
        return os.path.join(os.getcwd(), get_assets_dir(), 'resources')
    else:
        return os.path.join(os.path.dirname(wx.StandardPaths.Get().ExecutablePath), '..', 'resources')


def get_userconfig_path():
    return os.path.join(os.path.dirname(wx.StandardPaths.Get().UserConfigDir), 'VISTAS')


def get_resource_bitmap(name):
    return wx.Image(os.path.join(get_resources_directory(), 'images', name)).ConvertToBitmap()


def get_icon(name):
    return wx.Icon(wx.IconLocation(os.path.join(get_resources_directory(), 'images', name)))
