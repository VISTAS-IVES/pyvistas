from functools import reduce

import wx

from vistas.core.preferences import Preferences
from vistas.ui.controllers.project import ProjectChangedEvent
from vistas.ui.controls.viewer_panel import ViewerPanel


class ViewerContainerPanel(wx.Panel):
    class Row:
        def __init__(self):
            self.viewers = []
            self.num_viewers = 0
            self.prev_row = None

    def __init__(self, parent, id):
        super().__init__(parent, id)
        self.num_viewers = 0
        self.wireframe = False
        self.selection_view = False
        self.rows = []

        self.num_columns = Preferences.app().get('viewer_itemsperrow', 2)
        self.AddViewer()

        # Events
        self.Bind(wx.EVT_SIZE, self.OnSize)
        # Todo: VI_EVENT_CAMERA_MODE_CHANGED

    def __del__(self):
        pass  # Todo

    def AddViewer(self, new_viewer=None):
        # Add new row if necessary
        if self.num_viewers % self.num_columns == 0:
            self.AddRow()

        last_row = self.rows[-1]

        # Create new viewer
        if new_viewer is None:
            new_viewer = ViewerPanel(self, wx.ID_ANY)
        new_viewer.HideResizeAreas()
        new_viewer.ResetNeighbors()

        index = last_row.num_viewers
        last_row.viewers[index] = new_viewer
        last_row.num_viewers += 1
        self.num_viewers += 1

        # Size proportions for the new viewer
        new_viewer.width = 1/last_row.num_viewers
        new_viewer.height = 1/len(self.rows)

        for viewer in last_row.viewers[:index]:
            viewer.width *= index * (1/last_row.num_viewers)

        # Set neighbors
        if last_row.num_viewers > 1:
            new_viewer.SetNeighbor(last_row.viewers[index - 1], ViewerPanel.WEST)
            last_row.viewers[index-1].SetNeighbor(new_viewer, ViewerPanel.EAST)

        if last_row.prev_row is not None and last_row.prev_row.num_viewers >= last_row.num_viewers:
            for viewer in last_row.prev_row.viewers:
                new_viewer.SetNeighbor(viewer, ViewerPanel.NORTH)
                viewer.SetNeighbor(new_viewer, ViewerPanel.SOUTH)

        self.UpdateViewerSizes()

        # Todo: observable (?)

    def RemoveViewer(self, viewer=None):
        # Can't remove the last viewer
        if self.num_viewers < 2:
            return

        if viewer is None:
            row = self.rows[-1]
            viewer = row.viewers[row.num_viewers-1]

        for row in self.rows:
            if viewer in row.viewers:
                index = row.viewers.index(viewer)
                viewer = row.viewers[index]
                row.viewers[index] = None
                viewer.Destroy()
                self.num_viewers -= 1
                self.Rebuild()
                return

    def RefreshAllViewers(self):
        for row in self.rows:
            for viewer in row.viewers[:row.num_viewers]:
                viewer.gl_canvas.Refresh()

    def UpdateViewerSizes(self):
        for row in self.rows:
            for viewer in row.viewers[:row.num_viewers]:
                x = 0
                y = 0

                neighbor = viewer.GetNeighbor(ViewerPanel.WEST)
                if neighbor:
                    x = neighbor.GetPosition().x + neighbor.GetSize().GetWidth()

                neighbor = viewer.GetNeighbor(ViewerPanel.NORTH)
                if neighbor:
                    y = neighbor.GetPosition().y + neighbor.GetSize().GetHeight()

                viewer.SetSize(
                    x, y, self.GetSize().GetWidth() * viewer.width,
                    self.GetSize().GetHeight() * viewer.height
                )
                # viewer.gl_canvas.camera_controls.reposition_all()  # Todo

    def OnSize(self, event):
        self.UpdateViewerSizes()

    def Rebuild(self):
        rows = self.rows
        self.rows = []
        self.num_viewers = 0

        for row in rows:
            for viewer in (x for x in row.viewers if x is not None):
                self.AddViewer(viewer)

    def AddRow(self):
        new_row = self.Row()
        new_row.viewers = list(None for _ in range(self.num_columns))

        if self.rows:
            new_row.prev_row = self.rows[-1]

        for row in self.rows:
            for viewer in row.viewers[:row.num_viewers]:
                viewer.height *= len(self.rows) * (1/(len(self.rows)+1))

        self.rows.append(new_row)

    def ProjectChanged(self, event):
        if event.change == ProjectChangedEvent.PROJECT_RESET:
            while self.num_viewers > 1:
                self.RemoveViewer()
            self.GetMainViewerPanel().RefreshScenes()
            self.GetMainViewerPanel().UpdateLegend()

        else:
            for row in self.rows:
                for i in range(row.num_viewers):
                    row.viewers[i].ProjectChanged(event)

    def OnCameraModeChanged(self, event):
        pass  # Todo

    def GetMainViewerPanel(self):
        return self.rows[0].viewers[0]

    def GetAllViewerPanels(self):
        return reduce(lambda x, y: x + y, (row.viewers[:row.num_viewers] for row in self.rows))

    def ToggleWireframe(self):
        self.wireframe = not self.wireframe

        for viewer in self.GetAllViewerPanels():
            viewer.camera.wireframe = self.wireframe
            viewer.camera.scene.render_bounding_boxes = self.wireframe
            viewer.Refresh()

    def ToggleSelectionView(self):
        self.selection_view = not self.selection_view

        for viewer in self.GetAllViewerPanels():
            viewer.camera.selection_view = self.selection_view
            viewer.Refresh()

    def SyncAllCameras(self, do_sync, save_state):
        pass  # Todo
