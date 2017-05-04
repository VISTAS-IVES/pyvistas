import wx

from vistas.core.paths import get_resource_bitmap
from vistas.core.utils import get_platform
from vistas.ui.controllers.project import ProjectController
from vistas.ui.controls.project_panel import ProjectPanel
from vistas.ui.controls.viewer_container_panel import ViewerContainerPanel
from vistas.ui.controls.timeline_panel import TimelinePanel
from vistas.ui.controls.main_status_bar import MainStatusBar

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

        view_menu = wx.Menu()
        view_menu.Append(self.MENU_VIEW_ADD_VIEWER, '&Add Scene Viewer')
        view_menu.Append(self.MENU_VIEW_REMOVE_VIEWER, '&Remove Scene Viewer')
        view_menu.Append(self.MENU_VIEW_ADD_GRAPH, 'Add &Graph Viewer')
        view_menu.Append(self.MENU_VIEW_REMOVE_GRAPH, 'Remove Graph Viewer')
        view_menu.AppendSeparator()
        view_menu.Append(self.MENU_VIEW_COLLAPSE, '&Collapse Project Panel')
        menu_bar.Append(view_menu, '&View')
        
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
        main_splitter = wx.SplitterWindow(
            main_panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.SP_3DSASH | wx.SP_LIVE_UPDATE
        )
        left_panel = wx.Panel(main_splitter, wx.ID_ANY)
        right_panel = wx.Panel(main_splitter, wx.ID_ANY)
        self.viewer_container_panel = ViewerContainerPanel(right_panel, wx.ID_ANY)
        self.timeline_panel = TimelinePanel(right_panel, wx.ID_ANY)

        main_splitter.SplitVertically(left_panel, right_panel, 250)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)

        main_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        main_panel.SetSizer(main_panel_sizer)
        main_panel_sizer.Add(main_splitter, 1, wx.EXPAND)
        main_sizer.Add(main_panel, 1, wx.EXPAND)

        left_splitter = wx.SplitterWindow(
            left_panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.SP_3DSASH | wx.SP_LIVE_UPDATE
        )
        project_panel = ProjectPanel(left_splitter, wx.ID_ANY)
        options_panel = wx.Panel(left_splitter, wx.ID_ANY)  # Todo

        left_splitter.SplitHorizontally(project_panel, options_panel, 0)
        left_splitter.Unsplit(options_panel)

        left_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        left_panel.SetSizer(left_panel_sizer)
        left_panel_sizer.Add(left_splitter, 1, wx.EXPAND | wx.LEFT | wx.BOTTOM, 5)

        right_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        right_panel.SetSizer(right_panel_sizer)
        right_panel_sizer.Add(self.viewer_container_panel, 1, wx.EXPAND)
        right_panel_sizer.Add(self.timeline_panel, 0, wx.EXPAND)

        # Todo: expand button

        self.project_controller = ProjectController(project_panel)
        
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
            'main_splitter_pos': None,  # Todo
            'left_splitter_pos': None  # Todo
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
            pass  # Todo

        if state.get('left_splitter_pos') is not None:
            pass  # Todo
