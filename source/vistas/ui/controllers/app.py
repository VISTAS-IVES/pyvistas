import logging
import os

import wx
import wx.adv
from OpenGL.GL import *

from vistas import __version__ as version
from vistas.core import paths
from vistas.core.export import Exporter, ExportItem
from vistas.core.plugins.management import load_plugins
from vistas.core.preferences import Preferences
from vistas.core.timeline import Timeline
from vistas.ui.controllers.export import ExportController
from vistas.ui.windows.fly_scene_selector import FlythroughSceneSelector
from vistas.ui.windows.main import MainWindow
from vistas.ui.windows.plugins import PluginsWindow
from vistas.ui.windows.timeline_filter import TimeFilterWindow

logger = logging.getLogger(__name__)

PADDING = 5


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

        self.export_controller = ExportController()
        export_state = Preferences.app().get('export_window_state')
        if export_state:
            self.export_controller.LoadState(export_state)

        self.main_window.Bind(wx.EVT_MENU, self.OnWindowMenu)
        self.main_window.Bind(wx.EVT_CLOSE, self.OnWindowClose)

        self.timer = wx.Timer()
        self.timer.Bind(wx.EVT_TIMER, self.ShowSplashScreen)

        self.timer.Start(1, True)

    def ShowSplashScreen(self, event):
        gl_version = glGetString(GL_VERSION).decode()
        logger.debug('OpenGL Version: {}'.format(gl_version))

        splash_background = wx.Image(
            os.path.join(paths.get_resources_directory(), 'images', 'splash.png'), wx.BITMAP_TYPE_ANY
        ).ConvertToBitmap()
        splash_composite = wx.Bitmap(600, 200)
        
        dc = wx.MemoryDC(splash_composite)
        dc = wx.MemoryDC(splash_composite)
        dc.SetBackground(wx.Brush(wx.Colour(236, 236, 236)))
        dc.Clear()

        version_string = 'VISTAS Version: {} (Python)'.format(version)
        opengl_string = 'OpenGL Version: {}'.format(gl_version)

        dc.SetFont(wx.Font(12, wx.DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        version_extent = dc.GetTextExtent(version_string)
        opengl_extent = dc.GetTextExtent(opengl_string)

        dc.DrawBitmap(splash_background, 0, 0, True)
        dc.SetTextForeground(wx.Colour(0, 0, 0))
        dc.DrawText(version_string, 10, 195 - opengl_extent.y - version_extent.y)
        dc.DrawText(opengl_string, 10, 195 - opengl_extent.y)
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
            self.export_controller.RefreshExporter()
            self.export_controller.Reset()
        elif event_id == MainWindow.MENU_FILE_OPEN:
            self.main_window.project_controller.LoadProjectFromDialog()
            self.export_controller.RefreshExporter()
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
            self.main_window.AddGraphPanel()
        elif event_id == MainWindow.MENU_VIEW_REMOVE_GRAPH:
            self.main_window.RemoveGraphPanel()
        elif event_id == MainWindow.MENU_VIEW_COLLAPSE:
            self.main_window.ToggleProjectPanel()
        elif event_id == MainWindow.MENU_EXPORT_EXPORT:
            self.export_controller.SetExportWindow(self.GetDefaultExporter(True))
            self.export_controller.ShowWindow()
        elif event_id == MainWindow.MENU_EXPORT_CURRENT_COPY:
            self.RenderCurrentViewToClipboard()
        elif event_id == MainWindow.MENU_EXPORT_CURRENT_SAVE:
            self.RenderCurrentViewToFile()
        elif event_id == MainWindow.MENU_FLYTHROUGH_GENERATE:
            all_scenes = self.main_window.project_controller.project.all_scenes
            selector = FlythroughSceneSelector(all_scenes, None, wx.ID_ANY)
            if selector.ShowModal() == wx.ID_OK:
                selection = selector.GetSceneChoice()
                for i in range(len(all_scenes)):
                    if i == selection:
                        self.main_window.project_controller.AddFlythrough(all_scenes[i])

        elif event_id == MainWindow.MENU_SYNC_CAMERAS:
            sync = self.main_window.GetToolBar().FindById(MainWindow.MENU_SYNC_CAMERAS).IsToggled()
            self.main_window.viewer_container_panel.SyncAllCameras(sync, True)
        elif event_id == MainWindow.MENU_OPEN_TIMELINE_FILTER:
            if self.time_filter_window.timeline.enabled:
                self.time_filter_window.Show()
        elif event_id == MainWindow.MENU_WINDOW_PLUGINS:
            self.plugins_window.Show()
            self.plugins_window.Raise()
        elif event_id == MainWindow.MENU_DEBUG:
            pass
        elif event_id == MainWindow.MENU_DEBUG_TOGGLE_WIREFRAME:
            self.main_window.viewer_container_panel.ToggleWireframe()
        elif event_id == MainWindow.MENU_DEBUG_TOGGLE_SELECTION_VIEW:
            pass  # Todo
        elif event_id == MainWindow.MENU_HELP_REPORT_ISSUE:
            wx.LaunchDefaultBrowser('https://github.com/VISTAS-IVES/pyvistas/issues')

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

    def OnWindowClose(self, event: wx.CloseEvent):
        if self.main_window.project_controller.project.is_dirty and event.CanVeto():
            if wx.MessageBox(
                    "There is an unsaved project open. Do you still want to close VISTAS?", "Confirm Close?",
                    style=wx.ICON_QUESTION | wx.STAY_ON_TOP | wx.YES_NO | wx.NO_DEFAULT
               ) != wx.YES:
                event.Veto()
                return

        # Save preferences, exit now.
        prefs = Preferences.app()
        prefs['main_window_state'] = self.main_window.SaveState()
        prefs['export_window_state'] = self.export_controller.SaveState()
        prefs.save()
        wx.Exit()

    def GetDefaultExporter(self, add_labels=False):
        exporter = Exporter()
        viewerpanels = self.main_window.viewer_container_panel.GetAllViewerPanels()
        x_offset = 0
        y_offset = 0
        prev_height = 0
        i = 0
        num_columns = self.main_window.viewer_container_panel.num_columns
        for panel in viewerpanels:
            if i % num_columns == 0:
                x_offset = 0
                y_offset = prev_height
                prev_height = 0

            export_item = ExportItem(ExportItem.SCENE, (x_offset, y_offset), panel.GetSize().Get())
            export_item.camera = panel.camera
            for node in self.main_window.project_controller.project.all_scenes:
                if panel.camera.scene is node.scene:
                    export_item.project_node_id = node.node_id
                    exporter.add_item(export_item)

                    if add_labels:
                        label = ExportItem(ExportItem.LABEL)
                        label.size = (100, 100)
                        label.label = export_item.camera.scene.name
                        label.position = (int(x_offset + export_item.size[0] / 5 - 50),
                                          int(y_offset + export_item.size[1] / 5))
                        exporter.add_item(label)

                        timestamp = ExportItem(ExportItem.TIMESTAMP)
                        timestamp.time_format = Timeline.app().time_format
                        timestamp.position = (int(x_offset + export_item.size[0] / 2 - timestamp.size[0] / 2),
                                              int(y_offset + export_item.size[1] / 5))
                        exporter.add_item(timestamp)

                    x_offset += export_item.size[0] + PADDING
                    prev_height = max(prev_height, export_item.size[1] + PADDING)
                    i += 1

                    break

        x_offset = 0
        y_offset = prev_height

        for panel in self.main_window.graph_panels:
            if panel.visualization is not None:
                node = self.main_window.project_controller.project.find_visualization_node(panel.visualization)
                export_item = ExportItem(ExportItem.VISUALIZATION, (x_offset, y_offset),
                                         panel.GetSize().Get())
                export_item.viz_plugin = panel.visualization
                export_item.project_node_id = node.node_id
                exporter.add_item(export_item)
                y_offset += export_item.size[1] + PADDING

        exporter.fit_to_items()
        return exporter

    def RenderCurrentView(self):
        return self.GetDefaultExporter().export_current_frame()

    def RenderCurrentViewToClipboard(self):
        if wx.TheClipboard.Open():
            image = self.RenderCurrentView()
            wximage = wx.Image(*image.size)
            wximage.SetData(image.convert("RGB").tobytes())
            wx.TheClipboard.SetData(wx.BitmapDataObject(wximage.ConvertToBitmap()))

    def RenderCurrentViewToFile(self):
        fd = wx.FileDialog(self.main_window, "Choose a file", wildcard="*.png", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if fd.ShowModal() == wx.ID_OK:
            self.RenderCurrentView().save(fd.GetPath(), "PNG")
