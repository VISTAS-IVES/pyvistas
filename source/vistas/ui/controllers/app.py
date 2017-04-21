import os

import wx

from vistas.core.plugins.management import load_plugins
from vistas.ui.windows.main import MainWindow


class AppController(wx.EvtHandler):
    def __init__(self):
        builtin_plugin_dir = os.path.join(os.path.dirname(wx.StandardPaths.Get().ExecutablePath), '../Plugins')
        load_plugins(builtin_plugin_dir)

        self.main_window = MainWindow(None, wx.ID_ANY)
        self.main_window.Show()
