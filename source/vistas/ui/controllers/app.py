import os

import wx
import wx.adv
from OpenGL.GL import *

from vistas import __version__ as version
from vistas.core import paths
from vistas.core.plugins.management import load_plugins
from vistas.core.preferences import Preferences
from vistas.ui.windows.main import MainWindow
from vistas.ui.windows.plugins import PluginsWindow
from vistas.ui.windows.timeline_filter import TimeFilterWindow


class AppController(wx.EvtHandler):
    def __init__(self):
        super().__init__()
        load_plugins(paths.get_builtin_plugins_directory())

        self.main_window = MainWindow(None, wx.ID_ANY)
        self.main_window.Show()

        self.plugins_window = PluginsWindow(self.main_window, wx.ID_ANY)
        self.plugins_window.Hide()

        self.time_filter_window = TimeFilterWindow(self.main_window, wx.ID_ANY)
        self.time_filter_window.Hide()

        main_window_state = Preferences.app().get('main_window_state')
        if main_window_state:
            self.main_window.LoadState(main_window_state)

        self.main_window.Bind(wx.EVT_MENU, self.OnWindowMenu)
        self.main_window.Bind(wx.EVT_CLOSE, self.OnWindowClose)

        self.timer = wx.Timer()
        self.timer.Bind(wx.EVT_TIMER, self.ShowSplashScreen)

        self.timer.Start(1, True)

    def ShowSplashScreen(self, event):
        splash_background = wx.Image(
            os.path.join(paths.get_resources_directory(), 'images', 'splash.png'), wx.BITMAP_TYPE_ANY
        ).ConvertToBitmap()
        splash_composite = wx.Bitmap(500, 225)
        dc = wx.MemoryDC(splash_composite)
        version_string = 'VISTAS Version: {} (Python)'.format(version)
        opengl_string = 'OpenGL Version: {}'.format(glGetString(GL_VERSION).decode())

        dc.SetFont(wx.Font(12, wx.DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        version_extent = dc.GetTextExtent(version_string)
        opengl_extent = dc.GetTextExtent(opengl_string)

        dc.DrawBitmap(splash_background, 0, 0, True)
        dc.SetTextForeground(wx.Colour(0, 0, 0))
        dc.DrawText(version_string, 490 - version_extent.x, 210 - opengl_extent.y - version_extent.y)
        dc.DrawText(opengl_string, 490 - opengl_extent.x, 215 - opengl_extent.y)
        dc.SelectObject(wx.Bitmap())

        wx.adv.SplashScreen(
            splash_composite, wx.adv.SPLASH_TIMEOUT | wx.adv.SPLASH_CENTRE_ON_PARENT, 5000, self.main_window, wx.ID_ANY
        )

    def OnWindowMenu(self, event):
        event_id = event.GetId()

        if event_id == wx.ID_ABOUT:
            self.OnAboutMenuItem(event)
        elif event_id == wx.ID_EXIT:
            self.main_window.Close()
        elif event_id == MainWindow.MENU_FILE_NEW:
            self.main_window.project_controller.NewProject()
            self.main_window.options_panel.options = None
            # Todo - set ExportController project
            # Todo - reset ExportController items
        elif event_id == MainWindow.MENU_FILE_OPEN:
            self.main_window.project_controller.LoadProjectFromDialog()
            # Todo - set ExportControllerProject
        elif event_id == MainWindow.MENU_FILE_SAVE:
            self.main_window.project_controller.SaveProject()
        elif event_id == MainWindow.MENU_FILE_SAVEAS:
            self.main_window.project_controller.SaveProjectAs()
        elif event_id == MainWindow.MENU_FILE_ADDDATA:
            self.main_window.project_controller.AddDataFromFile(None)
        elif event_id == MainWindow.MENU_VIEW_ADD_VIEWER:
            self.main_window.viewer_container_panel.AddViewer()
        elif event_id == MainWindow.MENU_VIEW_REMOVE_VIEWER:
            self.main_window.viewer_container_panel.RemoveViewer()
        elif event_id == MainWindow.MENU_VIEW_ADD_GRAPH:
            pass
        elif event_id == MainWindow.MENU_VIEW_REMOVE_GRAPH:
            pass
        elif event_id == MainWindow.MENU_VIEW_COLLAPSE:
            self.main_window.ToggleProjectPanel()
        elif event_id == MainWindow.MENU_EXPORT_EXPORT:
            pass    # Todo - ExportController
        elif event_id == MainWindow.MENU_EXPORT_CURRENT_COPY:
            pass    # Todo - ExportController
        elif event_id == MainWindow.MENU_EXPORT_CURRENT_SAVE:
            pass    # Todo - ExportController
        elif event_id == MainWindow.MENU_FLYTHROUGH_GENERATE:
            pass    # Todo - implement GenerateFlythrough
        elif event_id == MainWindow.MENU_SYNC_CAMERAS:
            pass    # Todo - implement synced camera
        elif event_id == MainWindow.MENU_OPEN_TIMELINE_FILTER:
            if self.time_filter_window.timeline.enabled:
                self.time_filter_window.Show()
        elif event_id == MainWindow.MENU_WINDOW_PLUGINS:
            self.plugins_window.Show()
            self.plugins_window.Raise()
        elif event_id == MainWindow.MENU_DEBUG:
            pass
        elif event_id == MainWindow.MENU_DEBUG_TOGGLE_WIREFRAME:
            pass
        elif event_id == MainWindow.MENU_DEBUG_TOGGLE_SELECTION_VIEW:
            pass

    def OnAboutMenuItem(self, event):
        info = wx.adv.AboutDialogInfo()
        info.SetName('VISTAS')
        info.SetVersion(version, 'Version {} (Python)'.format(version))
        info.SetDescription('VISualization of Terrestrial-Aquatic Systems')
        info.SetCopyright('(c) 2008-2017 Conservation Biology Institute')
        info.AddDeveloper('Nikolas Stevenson-Molnar (nik.molnar@consbio.org')
        info.AddDeveloper('Taylor Mutch')
        info.AddDeveloper('Viriya Ratanasangpunth')
        info.AddDeveloper('Lee Zeman')

        wx.adv.AboutBox(info)

    def OnWindowClose(self, event):
        # Todo: check project save status
        wx.Exit()

