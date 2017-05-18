import wx

from vistas.core.paths import get_resource_bitmap
from vistas.core.utils import get_platform
from vistas.ui.events import *
from vistas.ui.controllers.project import ProjectController
from vistas.ui.controls.project_panel import ProjectPanel
from vistas.ui.controls.options_panel import OptionsPanel
from vistas.ui.controls.viewer_container_panel import ViewerContainerPanel
from vistas.ui.controls.timeline_panel import TimelinePanel
from vistas.ui.controls.main_status_bar import MainStatusBar
from vistas.ui.controls.expand_button import ExpandButton
from vistas.ui.windows.viz_dialog import VisualizationDialog


class MainWindow(wx.Frame):
    MENU_FILE_NEW = 101
    MENU_FILE_OPEN = 102
    MENU_FILE_SAVE = 103
    MENU_FILE_SAVEAS = 104
    MENU_FILE_ADDDATA = 105

    MENU_VIEW_ADD_VIEWER = 201
    MENU_VIEW_REMOVE_VIEWER = 202
    MENU_VIEW_ADD_GRAPH = 203
    MENU_VIEW_REMOVE_GRAPH = 204
    MENU_VIEW_COLLAPSE = 205

    MENU_EXPORT_EXPORT = 301
    MENU_EXPORT_CURRENT_COPY = 302
    MENU_EXPORT_CURRENT_SAVE = 303

    MENU_FLYTHROUGH_GENERATE = 401
    MENU_SYNC_CAMERAS = 402
    MENU_OPEN_TIMELINE_FILTER = 403

    MENU_WINDOW_PLUGINS = 501

    MENU_DEBUG = 601
    MENU_DEBUG_TOGGLE_WIREFRAME = 602
    MENU_DEBUG_TOGGLE_SELECTION_VIEW = 603

    def __init__(self, parent, id):
        super().__init__(parent, id, 'VISTAS')

        self.SetSize(1200, 800)
        self.CenterOnScreen()

        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        file_menu.Append(self.MENU_FILE_NEW, '&New Project\tCtrl+n')
        file_menu.AppendSeparator()
        file_menu.Append(self.MENU_FILE_OPEN, '&Open Project\tCtrl+o')
        file_menu.AppendSeparator()
        file_menu.Append(self.MENU_FILE_SAVE, '&Save Project\tCtrl+s')
        file_menu.Append(self.MENU_FILE_SAVEAS, 'Save Project &As...\tCtrl+Shift+s')
        file_menu.AppendSeparator()
        file_menu.Append(self.MENU_FILE_ADDDATA, 'Add &Data...')
        if get_platform() == 'windows':
            file_menu.AppendSeparator()
        file_menu.Append(wx.ID_ABOUT, '&About')
        file_menu.Append(wx.ID_PREFERENCES, '&Preferences')
        file_menu.Append(wx.ID_EXIT, '&Quit')
        menu_bar.Append(file_menu, '&File')

        self.view_menu = wx.Menu()
        self.view_menu.Append(self.MENU_VIEW_ADD_VIEWER, '&Add Scene Viewer')
        self.view_menu.Append(self.MENU_VIEW_REMOVE_VIEWER, '&Remove Scene Viewer')
        self.view_menu.Append(self.MENU_VIEW_ADD_GRAPH, 'Add &Graph Viewer')
        self.view_menu.Append(self.MENU_VIEW_REMOVE_GRAPH, 'Remove Graph Viewer')
        self.view_menu.AppendSeparator()
        self.view_menu.Append(self.MENU_VIEW_COLLAPSE, '&Collapse Project Panel')
        menu_bar.Append(self.view_menu, '&View')
        
        export_menu = wx.Menu()
        export_menu.Append(self.MENU_EXPORT_EXPORT, '&Export...\tCtrl+e')
        export_current_menu = wx.Menu()
        export_current_menu.Append(self.MENU_EXPORT_CURRENT_COPY, '&Copy to Clipboard')
        export_current_menu.Append(self.MENU_EXPORT_CURRENT_SAVE, '&Save to File...')
        export_menu.AppendSubMenu(export_current_menu, 'Current View')
        menu_bar.Append(export_menu, '&Export')

        window_menu = wx.Menu()
        window_menu.Append(self.MENU_WINDOW_PLUGINS, '&Plugins')
        menu_bar.Append(window_menu, '&Window')

        debug_menu = wx.Menu()
        debug_menu.Append(self.MENU_DEBUG_TOGGLE_WIREFRAME, 'Toggle &Wireframe')
        debug_menu.Append(self.MENU_DEBUG_TOGGLE_SELECTION_VIEW, 'Toggle &Selection View')
        menu_bar.Append(debug_menu, "&Debug")

        self.SetMenuBar(menu_bar)

        toolbar = self.CreateToolBar()
        toolbar.SetToolBitmapSize(wx.Size(20, 20))
        toolbar.AddTool(
            self.MENU_FILE_NEW, 'New Project', get_resource_bitmap('new_workspace.png'),
            'Create a new project (Ctrl+N)'
        )
        toolbar.AddTool(
            self.MENU_FILE_OPEN, 'Open Project', get_resource_bitmap('open_workspace.png'),
            'Open an existing project file (Ctrl+O)'
        )
        toolbar.AddTool(
            self.MENU_FILE_SAVE, 'Save Project', get_resource_bitmap('save_workspace.png'),
            'Save the current project (Ctrl+S)'
        )
        toolbar.AddSeparator()
        toolbar.AddTool(
            self.MENU_FILE_ADDDATA, 'Add Data', get_resource_bitmap('load_data.png'), 'Add data to project'
        )
        toolbar.AddSeparator()
        toolbar.AddTool(
            self.MENU_FLYTHROUGH_GENERATE, 'Create Flythrough', get_resource_bitmap('flythrough.png'),
            'Generate flythrough'
        )
        toolbar.AddTool(
            self.MENU_SYNC_CAMERAS, 'Sync Cameras', get_resource_bitmap('camera_sync.png'), 'Sync all viewer windows',
            wx.ITEM_CHECK
        )
        toolbar.AddSeparator()
        toolbar.AddTool(
            self.MENU_OPEN_TIMELINE_FILTER, 'Open Timeline Filter',
            get_resource_bitmap('glyphicons-541-hourglass.png'), 'Set timeline filter options'
        )
        toolbar.Realize()

        self.SetStatusBar(MainStatusBar(self, wx.ID_ANY))

        main_panel = wx.Panel(self, wx.ID_ANY)
        self.main_splitter = wx.SplitterWindow(
            main_panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.SP_3DSASH | wx.SP_LIVE_UPDATE
        )
        self.main_sash_position = None
        self.left_panel = wx.Panel(self.main_splitter, wx.ID_ANY)
        self.right_panel = wx.Panel(self.main_splitter, wx.ID_ANY)
        self.viewer_container_panel = ViewerContainerPanel(self.right_panel, wx.ID_ANY)
        self.timeline_panel = TimelinePanel(self.right_panel, wx.ID_ANY)

        self.main_splitter.SplitVertically(self.left_panel, self.right_panel, 250)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)

        main_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        main_panel.SetSizer(main_panel_sizer)
        main_panel_sizer.Add(self.main_splitter, 1, wx.EXPAND)
        main_sizer.Add(main_panel, 1, wx.EXPAND)

        self.left_splitter = wx.SplitterWindow(
            self.left_panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.SP_3DSASH | wx.SP_LIVE_UPDATE
        )
        self.left_sash_position = 0
        self.project_panel = ProjectPanel(self.left_splitter, wx.ID_ANY)

        # Todo - fix options_panel in main window
        self.options_panel = wx.Panel(self.left_splitter) # OptionsPanel(self.left_splitter, wx.ID_ANY)

        self.left_splitter.SplitHorizontally(self.project_panel, self.options_panel, 0)
        self.left_splitter.Unsplit(self.options_panel)

        left_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.left_panel.SetSizer(left_panel_sizer)
        left_panel_sizer.Add(self.left_splitter, 1, wx.EXPAND | wx.LEFT | wx.BOTTOM, 5)

        right_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.right_panel.SetSizer(right_panel_sizer)
        right_panel_sizer.Add(self.viewer_container_panel, 1, wx.EXPAND)
        right_panel_sizer.Add(self.timeline_panel, 0, wx.EXPAND)

        self.expand_button = ExpandButton(self.right_panel)

        self.project_controller = ProjectController(self.project_panel)
        self.Bind(EVT_COMMAND_PROJECT_CHANGED, self.OnProjectChanged)
        self.main_splitter.Bind(wx.EVT_SPLITTER_DCLICK, self.OnSplitterDClick)
        self.expand_button.Bind(wx.EVT_LEFT_DOWN, self.OnExpandButtonClick)

        # Listen to plugin events
        self.Bind(EVT_PLUGIN_OPTION, self.OnPluginOption)
        self.Bind(EVT_REDISPLAY, self.OnRedisplay)
        self.Bind(EVT_NEW_LEGEND, self.OnNewLegend)
        self.Bind(EVT_TIMELINE_CHANGED, self.OnTimeline)
        self.Bind(EVT_MESSAGE, self.OnMessage)

    def SerializeState(self):
        pos = self.GetPosition()
        size = self.GetSize()

        return {
            'display_index': wx.Display.GetFromWindow(self),
            'is_maximized': self.IsMaximized(),
            'x': pos.x,
            'y': pos.y,
            'w': size.x,
            'h': size.y,
            'main_splitter_pos': self.main_sash_position,
            'left_splitter_pos': self.left_sash_position
        }

    def LoadState(self, state):
        if state.get('display_index') is not None:
            display_area = wx.Display(state['display_index']).GetClientArea()
        else:
            display_area = wx.Display(0).GetClientArea()

        if all(state.get(x) for x in ('x', 'y', 'w', 'h')):
            pos = wx.Rect(state['x'], state['y'], state['w'], state['h'])

            if not display_area.Contains(pos):
                pos = display_area

            self.SetSize(pos)

        if state.get('is_maximized', False):
            self.Maximize()

        if state.get('main_splitter_pos') is not None:
            self.main_sash_position = state['main_splitter_pos']

        if state.get('left_splitter_pos') is not None:
            self.left_sash_position = state['left_splitter_pos']

    def OnProjectChanged(self, event):
        self.viewer_container_panel.ProjectChanged(event)

        changes = (
            ProjectChangedEvent.ADDED_VISUALIZATION, ProjectChangedEvent.RENAMED_ITEM, ProjectChangedEvent.DELETED_ITEM
        )

        if event.change in changes:
            pass  # Todo: graph panels

            self.project_controller.project.dirty = True

        elif event.change == ProjectChangedEvent.PROJECT_RESET:
            pass  # Todo: graph panels

            self.project_controller.project.dirty = True

    def OnPluginOption(self, event: PluginOptionEvent):
        if event.option and event.change is PluginOptionEvent.OPTION_CHANGED:
            for node in self.project_controller.project.all_visualizations:
                if event.plugin is node.visualization:
                    node.visualization.update_option(event.option)
                    #if self.options_panel.plugin is event.plugin:  # Todo - fix options_panel in main window
                    #    self.options_panel.Refresh()
                    break
        elif event.change is PluginOptionEvent.NEW_OPTIONS_AVAILABLE:
            pass    # Todo - fix options_panel in main window
            #self.options_panel.NewOptionAvailable(event)

    def OnRedisplay(self, event):
        for row in self.viewer_container_panel.rows:
            for viewer in row.viewers:
                if viewer is not None:
                    viewer.gl_canvas.Refresh()

    def OnNewLegend(self, event):
        pass    # Todo - legend_window

    def OnTimeline(self, event: TimelineEvent):
        # Update any existing visualization dialogs
        for win in VisualizationDialog.active_dialogs:
            win.TimelineChanged()

        # Update timeline ctrl
        self.timeline_panel.timeline_ctrl.TimelineChanged()

        # Update viz plugins
        for node in self.project_controller.project.all_visualizations:
            node.visualization.timeline_changed()

    def OnMessage(self, event: MessageEvent):
        if event.level is MessageEvent.NORMAL:
            wx.MessageBox(event.msg, "Message - Normal", style=wx.OK | wx.ICON_INFORMATION)
        elif event.level is MessageEvent.ERROR:
            wx.MessageBox(event.msg, "Message - Error", style=wx.OK | wx.ICON_EXCLAMATION)
        elif event.level is MessageEvent.CRITICAL:
            wx.MessageBox(event.msg, "Message - Critical Error", style=wx.OK | wx.ICON_ERROR)
            wx.MessageBox("VISTAS will now exit.", "Message - Critical Error", style=wx.OK | wx.ICON_ERROR)
            exit(1)

    def ToggleProjectPanel(self):
        if self.main_splitter.IsSplit():
            self.CollapseProjectPanel()
        else:
            self.RestoreProjectPanel()
        self.InvalidateBestSize()
        self.Refresh()

    def CollapseProjectPanel(self):
        self.main_sash_position = self.main_splitter.GetSashPosition()
        self.main_splitter.Unsplit(self.left_panel)
        self.expand_button.expanded = False
        self.view_menu.SetLabel(self.MENU_VIEW_COLLAPSE, '&Expand Project Panel')

    def RestoreProjectPanel(self):
        self.main_splitter.SplitVertically(self.left_panel, self.right_panel, self.main_sash_position)
        self.main_sash_position = None
        self.expand_button.expanded = True
        self.view_menu.SetLabel(self.MENU_VIEW_COLLAPSE, '&Collapse Project Panel')
        self.timeline_panel.Refresh()

    def OnSplitterDClick(self, event):
        self.CollapseProjectPanel()

    def OnExpandButtonClick(self, event):
        self.ToggleProjectPanel()

    def SetOptions(self, options=None, plugin=None):
        pass    # Todo - fix options_panel in main window
        #if options and plugin:
        #    self.left_splitter.SplitHorizontally(self.project_panel, self.options_panel, self.left_sash_position)
        #    self.options_panel.options = options
        #    self.options_panel.plugin = plugin
        #    self.options_panel.Layout()
        #    self.options_panel.FitInside()
        #else:
        #    self.options_panel.options = None
        #    self.left_sash_position = self.left_splitter.GetSashPosition()
        #    self.left_splitter.Unsplit(self.options_panel)
