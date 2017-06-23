from vistas.core.export import Exporter, ExportItem
from vistas.ui.project import Project
from vistas.ui.windows.export import ExportFrame
from vistas.ui.windows.export_scene_dialog import ExportSceneDialog

import wx


class ExportController(wx.EvtHandler):
    def __init__(self):
        super().__init__()
        self.export_frame = ExportFrame(None, wx.ID_ANY)
        self.project = Project.get()
        self.frame_position = wx.DefaultPosition
        self.canvas_size = None
        self.export_frame.Hide()
        self.export_frame.SetCanvasSize(*self.project.exporter.size)

    def __del__(self):
        self.export_frame.Destroy()

    def Reset(self):
        self.export_frame.canvas.DeleteAllItems()

    def ShowWindow(self):
        self.export_frame.SetPosition(self.frame_position)
        self.export_frame.Show()
        self.export_frame.Raise()

    def SetExportWindow(self, exporter: Exporter):
        self.Reset()
        if self.project.exporter.items:
            for item in exporter.items:
                self.project.exporter.add_item(item)
            size = exporter.size
            self.project.exporter.size = size
            self.export_frame.SetCanvasSize(*size)
            self.canvas_size = size
        else:
            size = self.project.exporter.size

            if self.canvas_size is None:
                self.canvas_size = size
            elif not (self.canvas_size == size):
                size = self.canvas_size
            self.project.exporter.size = size
            self.export_frame.SetCanvasSize(*size)

        for item in self.project.exporter.items:
            canvas_item = self.export_frame.canvas.AddItem(item)
            canvas_item.Bind(wx.EVT_LEFT_DOWN, self.OnItemLeftDown)
            canvas_item.Bind(wx.EVT_LEFT_DCLICK, self.OnItemDClick)
            canvas_item.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)

    def OnFrameClose(self, event):
        self.frame_position = self.export_frame.GetPosition()
        self.canvas_size = self.export_frame.width_text.GetValue(), self.export_frame.height_text.GetValue()
        self.export_frame.canvas.DeselectItem()
        self.export_frame.Hide()
        event.Skip(False)

    def OnSizeTextChange(self, event):
        size = self.export_frame.width_text.GetValue(), self.export_frame.height_text.GetValue()
        self.project.exporter.size = size
        self.export_frame.SetCanvasSize(*size)

    def OnFitFrameButton(self, event):
        self.project.exporter.fit_to_items()
        self.export_frame.SetCanvasSize(self.project.exporter.size)
        self.export_frame.Refresh()

    def OnExportButton(self, event):
        pass    # Todo - implement

    def OnLeftDown(self, event):
        focus_win = wx.Window.FindFocus()
        if focus_win is not None:
            evt = wx.FocusEvent()
            evt.SetEventObject(focus_win)
            wx.PostEvent(focus_win, evt)

        self.export_frame.canvas.SetFocus()
        self.export_frame.canvas.DeselectItem()

    def OnRightDown(self, event):
        pass    # Todo - implement

    def OnPopupMenu(self, event):
        pass    # Todo - implement

    def OnItemLeftDown(self, event):
        self.export_frame.canvas.SelectItem(event.GetEventObject())
        event.Skip(True)

    def OnItemDClick(self, event):
        pass    # Todo - implement

    def CreateExportSceneDialog(self, item: ExportItem):
        config = ExportSceneDialog(self.export_frame.canvas, wx.ID_ANY, item)
        config.CenterOnParent()
        config.ShowModal()

    def CleanTextInput(self, string):
        pass    # Todo - is this needed anymore? Probably...

    def OnTextUpdate(self, event):
        pass    # Todo - implement

    def OnTextEndInput(self, event):
        pass

    def OnTextTimer(self, event):
        pass
