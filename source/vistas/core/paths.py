import os

import wx

from vistas.core.utils import get_platform


def get_builtin_plugins_directory():
    if get_platform() == 'windows':
        return os.path.join(os.getcwd(), '..', 'plugins')
    else:
        return os.path.join(os.path.dirname(wx.StandardPaths.Get().ExecutablePath), '..', 'plugins')


def get_resources_directory():
    if get_platform() == 'windows':
        return os.path.join(os.getcwd(), '..', 'resources')
    else:
        return os.path.join(os.path.dirname(wx.StandardPaths.Get().ExecutablePath), '..', 'resources')
