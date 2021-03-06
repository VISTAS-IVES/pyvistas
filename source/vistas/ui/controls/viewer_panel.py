import wx
from shapely.geometry import LinearRing
from wx.glcanvas import WX_GL_MINOR_VERSION
from wx.glcanvas import WX_GL_RGBA, WX_GL_DOUBLEBUFFER, WX_GL_DEPTH_SIZE, WX_GL_CORE_PROFILE, WX_GL_MAJOR_VERSION

from vistas.core.graphics.camera import Camera
from vistas.core.observers.camera import CameraObservable
from vistas.core.observers.interface import Observer
from vistas.core.paths import get_resource_bitmap
from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.visualization import VisualizationPlugin3D
from vistas.ui.controllers.project import ProjectChangedEvent
from vistas.ui.controls.gl_canvas import GLCanvas
from vistas.ui.events import CameraSelectFinishEvent, EVT_CAMERA_SELECT_FINISH
from vistas.ui.project import Project
from vistas.ui.utils import post_message
from vistas.ui.windows.inspect import InspectWindow
from vistas.ui.windows.legend import LegendWindow
from vistas.ui.windows.zonalstats import ZonalStatisticsWindow


class ViewerPanel(wx.Panel, Observer):
    """
    Container for rendering a 3D visualization. Controls which 3D visualization is currently being rendered and
    how to resize itself relative to it's neighbors in the parent window.
    """

    NORTH = 'north'
    EAST = 'east'
    SOUTH = 'south'
    WEST = 'west'

    POPUP_COPY = 1

    inspect_window = None   # InspectWindow
    zonalstats_window = None    # ZonalStatisticsWindow

    def __init__(self, parent, id):
        super().__init__(parent, id)

        self.north = []
        self.east = None
        self.south = []
        self.west = None
        self.width = 1.
        self.height = 1.

        self.resizing_north = False
        self.resizing_east = False
        self.resizing_south = False
        self.resizing_west = False
        self.last_pos = None

        self.scenes = []
        self.selected_scene = None
        self.saved_interactor_state = None
        self.reset_interactor = False

        self.parent = parent
        self.north_resize_area = wx.Window(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(-1, 2))
        self.east_resize_area = wx.Window(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(2, -1))
        self.south_resize_area = wx.Window(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(-1, 2))
        self.west_resize_area = wx.Window(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(2, -1))

        self.north_resize_area.SetCursor(wx.Cursor(wx.CURSOR_SIZENS))
        self.east_resize_area.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))
        self.south_resize_area.SetCursor(wx.Cursor(wx.CURSOR_SIZENS))
        self.west_resize_area.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))

        self.scene_choice = wx.Choice(self, wx.ID_ANY)
        self.scene_choice.SetToolTip('Select a scene to view')

        self.legend_button = wx.BitmapButton(self, wx.ID_ANY, get_resource_bitmap('stripes.png'))
        self.legend_button.SetToolTip('Show/hide legend')

        self.camera = Camera(observable=True)

        attrib_list = [
            WX_GL_RGBA, WX_GL_DOUBLEBUFFER, WX_GL_DEPTH_SIZE, 16, WX_GL_CORE_PROFILE, 
            WX_GL_MAJOR_VERSION, 3, WX_GL_MINOR_VERSION, 3
        ]

        self.gl_canvas = GLCanvas(
            self, wx.ID_ANY, self.camera, attrib_list=attrib_list, can_sync=True
        )
        self.gl_canvas.Refresh()

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(self.scene_choice, 1, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        top_sizer.Add(self.legend_button, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 3)

        content_sizer = wx.BoxSizer(wx.VERTICAL)
        content_sizer.Add(top_sizer, 0, wx.EXPAND | wx.ALL, 5)
        content_sizer.Add(self.gl_canvas, 1, wx.EXPAND)

        center_sizer = wx.BoxSizer(wx.HORIZONTAL)
        center_sizer.Add(self.west_resize_area, 0, wx.EXPAND)
        center_sizer.Add(content_sizer, 1, wx.EXPAND)
        center_sizer.Add(self.east_resize_area, 0, wx.EXPAND)

        sizer.Add(self.north_resize_area, 0, wx.EXPAND)
        sizer.Add(center_sizer, 1, wx.EXPAND)
        sizer.Add(self.south_resize_area, 0, wx.EXPAND)

        # Event handlers
        self.scene_choice.Bind(wx.EVT_CHOICE, self.OnSceneChoice)
        self.legend_button.Bind(wx.EVT_BUTTON, self.OnLegendLabel)

        self.north_resize_area.Bind(wx.EVT_LEFT_DOWN, self.OnResizeLeftDown)
        self.north_resize_area.Bind(wx.EVT_LEFT_UP, self.OnResizeLeftUp)
        self.north_resize_area.Bind(wx.EVT_MOTION, self.OnResizeMotion)

        self.east_resize_area.Bind(wx.EVT_LEFT_DOWN, self.OnResizeLeftDown)
        self.east_resize_area.Bind(wx.EVT_LEFT_UP, self.OnResizeLeftUp)
        self.east_resize_area.Bind(wx.EVT_MOTION, self.OnResizeMotion)

        self.south_resize_area.Bind(wx.EVT_LEFT_DOWN, self.OnResizeLeftDown)
        self.south_resize_area.Bind(wx.EVT_LEFT_UP, self.OnResizeLeftUp)
        self.south_resize_area.Bind(wx.EVT_MOTION, self.OnResizeMotion)

        self.west_resize_area.Bind(wx.EVT_LEFT_DOWN, self.OnResizeLeftDown)
        self.west_resize_area.Bind(wx.EVT_LEFT_UP, self.OnResizeLeftUp)
        self.west_resize_area.Bind(wx.EVT_MOTION, self.OnResizeMotion)

        self.gl_canvas.Bind(wx.EVT_LEFT_DCLICK, self.OnCanvasDClick)
        self.gl_canvas.Bind(wx.EVT_RIGHT_DOWN, self.OnCanvasRightClick)

        self.gl_canvas.camera.wireframe = False
        self.gl_canvas.SetFocus()

        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.Bind(EVT_CAMERA_SELECT_FINISH, self.OnDragSelectFinish)

        self.legend_window = LegendWindow(self, wx.ID_ANY)

        self.RefreshScenes()

        observable = CameraObservable.get()
        observable.add_observer(self)
        self.reset_interactor = observable.is_sync

    def OnDestroy(self, event):
        CameraObservable.get().remove_observer(self)
        event.Skip()

    def SetNeighbor(self, neighbor, direction):
        if direction == self.NORTH:
            self.north_resize_area.Show()
            self.north.append(neighbor)

        elif direction == self.EAST:
            self.east_resize_area.Show()
            self.east = neighbor

        elif direction == self.SOUTH:
            self.south_resize_area.Show()
            self.south.append(neighbor)

        elif direction == self.WEST:
            self.west_resize_area.Show()
            self.west = neighbor

    def GetNeighbor(self, direction):
        if direction == self.NORTH:
            return self.north[0] if self.north else None

        elif direction == self.EAST:
            return self.east

        elif direction == self.SOUTH:
            return self.south[0] if self.south else None

        elif direction == self.WEST:
            return self.west

    def RemoveNeighbor(self, neighbor):
        self.north.remove(neighbor)

        if self.east == neighbor:
            self.east = None

        self.south.remove(neighbor)

        if self.west == neighbor:
            self.west = None

    def ResetNeighbors(self):
        self.north = []
        self.east = None
        self.south = []
        self.west = None

    def HideResizeAreas(self):
        self.north_resize_area.Hide()
        self.east_resize_area.Hide()
        self.south_resize_area.Hide()
        self.west_resize_area.Hide()

    def UpdateScene(self):
        for i, scene in enumerate(self.scenes):
            if i == self.scene_choice.GetSelection():
                observable = CameraObservable.get()
                if observable.is_sync:
                    interactor = self.saved_interactor_state
                else:
                    interactor = self.gl_canvas.camera_interactor
                interactor.camera.scene = scene
                if not observable.is_sync:
                    interactor.reset_position()
                self.selected_scene = scene
        self.gl_canvas.Refresh()

    def OnResizeLeftDown(self, event):
        self.resizing_north = self.resizing_east = self.resizing_south = self.resizing_west = False

        if event.GetEventObject() == self.north_resize_area:
            self.resizing_north = True
            self.last_pos = event.y

            self.north_resize_area.CaptureMouse()

        elif event.GetEventObject() == self.east_resize_area:
            self.resizing_east = True
            self.last_pos = event.x

            self.east_resize_area.CaptureMouse()

        elif event.GetEventObject() == self.south_resize_area:
            self.resizing_south = True
            self.last_pos = event.y

            self.south_resize_area.CaptureMouse()

        elif event.GetEventObject() == self.west_resize_area:
            self.resizing_west = True
            self.last_pos = event.x

            self.west_resize_area.CaptureMouse()

    def OnResizeLeftUp(self, event):
        self.resizing_north = self.resizing_east = self.resizing_south = self.resizing_west = False

        if self.north_resize_area.HasCapture():
            self.north_resize_area.ReleaseMouse()
        if self.east_resize_area.HasCapture():
            self.east_resize_area.ReleaseMouse()
        if self.south_resize_area.HasCapture():
            self.south_resize_area.ReleaseMouse()
        if self.west_resize_area.HasCapture():
            self.west_resize_area.ReleaseMouse()

    def OnResizeMotion(self, event):
        if self.resizing_north:
            diff = self.last_pos - event.y
            parent_height = self.GetParent().GetSize().GetHeight()
            prop_diff = diff / parent_height

            self.height += prop_diff

            # Update neighbors to the east
            east = self.east
            while east is not None:
                east.height += prop_diff
                east = east.east

            # Update neighbors to the west
            west = self.west
            while west is not None:
                west.height += prop_diff
                west = west.west

            for viewer in self.north:
                viewer.height -= prop_diff

        elif self.resizing_east:
            diff = event.x - self.last_pos
            parent_width = self.GetParent().GetSize().GetWidth()
            prop_diff = diff / parent_width

            self.width += prop_diff
            self.east.width -= prop_diff

        elif self.resizing_south:
            diff = event.y - self.last_pos
            parent_height = self.GetParent().GetSize().GetHeight()
            prop_diff = diff / parent_height

            self.height += prop_diff

            # Update neighbors to the east
            east = self.east
            while east is not None:
                east.height += prop_diff
                east = east.east

            # Update neighbors to the west
            west = self.west
            while west is not None:
                west.height += prop_diff
                west = west.west

            for viewer in self.south:
                viewer.height -= prop_diff

        elif self.resizing_west:
            diff = self.last_pos - event.x
            parent_width = self.GetParent().GetSize().GetWidth()
            prop_diff = diff / parent_width

            self.width += prop_diff
            self.west.width -= prop_diff

        self.GetParent().UpdateViewerSizes()

    def OnCanvasDClick(self, event: wx.MouseEvent):
        if self.gl_canvas.selection_mode:
            event.Skip()
            return

        size = self.gl_canvas.GetSize()
        mouse_x = event.GetX() / size.x * 2 - 1
        mouse_y = - event.GetY() / size.y * 2 + 1
        intersects = self.gl_canvas.camera.raycaster.intersect_objects((mouse_x, mouse_y), self.camera)
        if intersects:
            intersection = intersects[0]
            plugin = intersection.object.plugin
            if plugin is not None:
                result = plugin.get_identify_detail(intersection.point)
                if self.inspect_window is None:
                    self.inspect_window = InspectWindow(self, wx.ID_ANY)
                self.inspect_window.data = result
                self.inspect_window.Show()

                zonal_result = plugin.get_zonal_stats_from_point(intersection.point)
                if zonal_result:
                    if self.zonalstats_window is None:
                        self.zonalstats_window = ZonalStatisticsWindow(self, wx.ID_ANY)
                    self.zonalstats_window.data = zonal_result
                    self.zonalstats_window.plugin = plugin
                    self.zonalstats_window.Show()

    def OnDragSelectFinish(self, event: CameraSelectFinishEvent):
        plugin = event.plugin
        points = event.points
        if len(points) >= 3:
            result = plugin.get_zonal_stats_from_feature(LinearRing([p for p in points + [points[0]]]))
            if result:
                if self.zonalstats_window is None:
                    self.zonalstats_window = ZonalStatisticsWindow(self, wx.ID_ANY)
                self.zonalstats_window.data = result
                self.zonalstats_window.plugin = plugin
                self.zonalstats_window.Show()
        else:
            post_message("At least 3 points are required to do zonal statistics!", 1)

    def OnCanvasRightClick(self, event):
        if self.gl_canvas.selection_mode:
            event.Skip()
            return

        menu = wx.Menu()
        menu.Append(self.POPUP_COPY, 'Copy')
        menu.Bind(wx.EVT_MENU, self.OnCanvasPopupMenu)

        self.PopupMenu(menu)

    def OnCanvasPopupMenu(self, event):
        if event.GetId() == self.POPUP_COPY:
            if wx.TheClipboard.IsOpened():
                opened = True
            else:
                opened = wx.TheClipboard.Open()

            if opened:
                size = self.gl_canvas.GetSize()
                im = self.gl_canvas.camera.render_to_bitmap(size.x, size.y)
                wx_image = wx.Image(size.x, size.y)
                wx_image.SetData(im.convert('RGB').tobytes())
                wx.TheClipboard.SetData(wx.BitmapDataObject(wx_image.ConvertToBitmap()))

    def RefreshScenes(self):
        visualization_root = Project.get().visualization_root
        self.scenes = []
        self.FetchScenes(visualization_root)

        self.scene_choice.Clear()

        for i, scene in enumerate(self.scenes):
            self.scene_choice.Append(scene.name)
            if scene == self.selected_scene:
                self.scene_choice.SetSelection(i)

        # If not valid scene is currently selected and a scene exists, select it
        if self.scenes and (not self.selected_scene or self.selected_scene.name != self.scene_choice.GetStringSelection()):
            self.scene_choice.SetSelection(0)
            self.scene_choice.AddPendingEvent(wx.CommandEvent(wx.wxEVT_CHOICE))

    def FetchScenes(self, root):
        for node in root.children:
            if node.is_scene:
                self.scenes.append(node.scene)
            elif node.is_folder:
                self.FetchScenes(node)

    def ProjectChanged(self, event):
        # Recenter camera when a visualization is added to the current scene
        if event.change == ProjectChangedEvent.ADDED_VISUALIZATION:
            node = event.node
            if node is not None and node.is_visualization:
                if isinstance(node.visualization, VisualizationPlugin3D):
                    parent = node.parent
                    while parent is not None and not parent.is_scene:
                        parent = parent.parent

                    if parent is not None and parent.is_scene:
                        if parent.scene == self.selected_scene:
                            self.gl_canvas.camera_interactor.reset_position()

        else:
            self.RefreshScenes()
            self.gl_canvas.Refresh()
            self.UpdateLegend()

        self.UpdateOverlay()

    def UpdateOverlay(self):
        self.UpdateScene()
        plugins = Project.get().find_viz_with_parent_scene(self.selected_scene)

        viz = None
        for p in plugins:
            if isinstance(p, VisualizationPlugin3D):
                viz = p

        if viz is not None:
            # If the visualization has a raster, show the selection controls
            for i, role in enumerate(viz.data_roles):
                if role[0] == DataPlugin.RASTER and viz.get_data(i) is not None:
                    self.gl_canvas.selection_controls.show()
                    return

        self.gl_canvas.selection_controls.hide()

    def OnSceneChoice(self, event):
        self.UpdateScene()

    def OnLegendLabel(self, event):
        if self.legend_window.IsShown():
            self.legend_window.HideWindow()
            return
        self.UpdateLegend()
        self.legend_window.ShowWindow()
        self.legend_window.Refresh()

    def VizHasNewLegend(self):
        self.UpdateLegend()
        self.parent.RefreshAllViewers()

    def UpdateLegend(self):
        plugins = Project.get().find_viz_with_parent_scene(self.selected_scene)
        if plugins:
            for p in plugins:
                if p.has_legend and isinstance(p, VisualizationPlugin3D):
                    self.legend_window.visualization = p
                    break
                else:
                    self.legend_window.visualization = None
        else:
            self.legend_window.visualization = None
        self.legend_window.RefreshLegend()

    def ResetCameraInteractor(self):
        observable = CameraObservable.get()
        if observable.is_sync:
            self.reset_interactor = True
        else:
            self.gl_canvas.camera_interactor.reset_position()

    def update(self, observable: CameraObservable):
        if observable.is_sync:
            interactor = observable.global_interactor
            if observable.need_state_saved:
                self.saved_interactor_state = self.gl_canvas.camera_interactor
            self.gl_canvas.camera_interactor = interactor
            self.gl_canvas.camera_controls.reset()
        else:
            if self.saved_interactor_state is not None:
                self.gl_canvas.camera_interactor = self.saved_interactor_state
            self.saved_interactor_state = None
            if self.reset_interactor:
                self.gl_canvas.camera_interactor.reset_position()
                self.reset_interactor = False
            self.gl_canvas.camera_controls.reset()
