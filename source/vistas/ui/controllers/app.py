import os

import wx
import wx.adv

from vistas import __version__ as version
from vistas.core import paths
from vistas.core.plugins.management import load_plugins
from vistas.core.preferences import Preferences
from vistas.ui.windows.main import MainWindow


class AppController(wx.EvtHandler):
    def __init__(self):
        load_plugins(paths.get_builtin_plugins_directory())

        self.main_window = MainWindow(None, wx.ID_ANY)
        self.main_window.Show()

        main_window_state = Preferences.app().get('main_window_state')
        if main_window_state:
            self.main_window.load_state(main_window_state)

        self.main_window.Bind(wx.EVT_MENU, self.on_window_menu)
        self.main_window.Bind(wx.EVT_CLOSE, self.on_window_close)

        splash_background = wx.Image(
            os.path.join(paths.get_resources_directory(), 'images', 'splash.png'), wx.BITMAP_TYPE_ANY
        ).ConvertToBitmap()
        splash_composite = wx.Bitmap(500, 225)
        dc = wx.MemoryDC(splash_composite)
        version_string = 'VISTAS Version: {} (Python)'.format(version)
        opengl_string = 'OpenGL Version: (TODO)'

        dc.SetFont(wx.Font(12, wx.DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        version_extent = dc.GetTextExtent(version_string)
        opengl_extent = dc.GetTextExtent(opengl_string)

        dc.DrawBitmap(splash_background, 0, 0, True)
        dc.SetTextForeground(wx.Colour(0, 0, 0))
        dc.DrawText(version_string, 490 - version_extent.x, 210 - opengl_extent.y - version_extent.y)
        dc.DrawText(opengl_string, 490 - version_extent.x, 215 - opengl_extent.y)
        dc.SelectObject(wx.Bitmap())

        wx.adv.SplashScreen(
            splash_composite, wx.adv.SPLASH_TIMEOUT | wx.adv.SPLASH_CENTRE_ON_PARENT, 5000, self.main_window, wx.ID_ANY
        )

    def on_window_menu(self, event):
        event_id = event.GetId()

        if event_id == wx.ID_ABOUT:
            self.on_about_menu_item(event)
        elif event_id ==wx.ID_EXIT:
            self.main_window.Close()

        # Todo

    def on_window_close(self, event):
        # Todo: check project save status
        wx.Exit()

