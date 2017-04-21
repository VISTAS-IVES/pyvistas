import os

import wx


def get_builtin_plugins_directory():
    return os.path.join(os.path.dirname(wx.StandardPaths.Get().ExecutablePath), '../plugins')


def get_resources_directory():
    return os.path.join(os.path.dirname(wx.StandardPaths.Get().ExecutablePath), '../resources')
