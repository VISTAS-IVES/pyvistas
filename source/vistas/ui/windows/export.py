from vistas.core.export import Exporter, ExportItem

import wx
import wx.lib.intctrl


class ExportItemBitmap(wx.EvtHandler):

    def __init__(self, canvas, item: ExportItem):
        pass

    def Select(self):
        pass

    def Deselect(self):
        pass

    # IsSelected?

    def Draw(self, dc: wx.DC):
        pass

    def Refresh_cache(self):
        pass

    def OnMotion(self, event):
        pass

    def OnLeftDown(self, event):
        pass

    def OnLeftUp(self, event):
        pass


class ExportCanvas(wx.ScrolledWindow):

    def __init__(self, parent, id):
        pass

    def __del__(self):
        pass

    def CopyEvent(self, event):
        pass

    def Cleanup(self):
        pass

    def AddItem(self, item: ExportItem) -> ExportItemBitmap:
        pass

    def DeleteItem(self, item: ExportItemBitmap):
        pass

    def DeleteAllItems(self):
        pass

    def CaptureItem(self, item: ExportItemBitmap):
        pass

    def ReleaseItem(self):
        pass

    def SelectItem(self, item: ExportItemBitmap):
        pass

    def DeselectItem(self):
        pass

    def RefreshItemCache(self, item: ExportItem):
        pass

    def SendToFront(self, item: ExportItemBitmap):
        pass

    def SendToBack(self, item: ExportItemBitmap):
        pass

    def OnEraseBackground(self, event):
        pass

    def OnSize(self, event: wx.SizeEvent):
        pass

    def OnScroll(self, event: wx.ScrollEvent):
        pass

    def OnPaint(self, event: wx.PaintEvent):
        pass

    def OnMouse(self, event: wx.MouseEvent):
        pass

    def OnCaptureLost(self, event: wx.MouseCaptureLostEvent):
        pass


class ExportFrame(wx.Frame):

    def __init__(self, parent, id):
        super().__init__(parent, id, "Export Animation", style=wx.DEFAULT_FRAME_STYLE)

        main_panel = wx.Panel(self, wx.ID_ANY)
        width_static = wx.StaticText(main_panel, wx.ID_ANY, "Width:")
        self.width_text = wx.lib.intctrl.IntCtrl(main_panel, wx.ID_ANY, value=600)
        height_static = wx.StaticText(main_panel, wx.ID_ANY, "Height:")
        self.height_text = wx.TextCtrl(main_panel, wx.ID_ANY, value=800)
        self.canvas = ExportCanvas(main_panel, wx.ID_ANY)
        self.fit_frame_button = wx.Button(main_panel, wx.ID_ANY, "Fit Window")
        self.fit_frame_button.SetToolTip("Fits exporter width and height to the size of items in the window")
        self.export_button = wx.Button(main_panel, wx.ID_ANY, "Export")
        self.export_button.SetDefault()

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)

        main_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        main_panel.SetSizer(main_panel_sizer)

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(width_static, 0, wx.RIGHT, 5)
        top_sizer.Add(self.width_text, 0, wx.RIGHT, 10)
        top_sizer.Add(height_static, 0, wx.RIGHT, 5)
        top_sizer.Add(self.height_text)

        main_panel_sizer.Add(top_sizer, 0, wx.EXPAND | wx.ALL, 10)
        main_panel_sizer.Add(self.canvas, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.fit_frame_button)
        button_sizer.AddStretchSpacer(1)
        button_sizer.Add(self.export_button)

        main_panel_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        main_sizer.Add(main_panel, 1, wx.EXPAND)
        self.Bind(wx.EVT_MAXIMIZE, self.OnMaximize)

    def SetCanvasSize(self, width, height):
        self.SetMaxSize(wx.Size(-1, -1))
        size = wx.Size(width, height)
        self.canvas.SetMinSize(size)
        self.canvas.SetMaxSize(size)
        self.width_text.SetValue("{}".format(width))
        self.height_text.SetValue("{}".format(height))
        self.canvas.SetClientSize(size)
        self.canvas.SetScrollRate(1, 1)
        self.canvas.SetVirtualSize(size)
        self.Fit()
        self.SetMaxSize(self.GetSize())

    def OnMaximize(self, event: wx.MaximizeEvent):
        self.Restore()
        self.Fit()
        wx.PostEvent(self.canvas, wx.SizeEvent(self.GetSize()))
