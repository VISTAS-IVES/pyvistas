import wx
from PIL import Image

from vistas.ui.controls.static_image import StaticImage
from vistas.ui.utils import make_window_transparent


class LegendWindow(wx.Frame):

    RESET_LEGEND = 0

    def __init__(self, parent, id):
        super().__init__(parent, id, size=wx.Size(140, 300), style=wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT)
        self.max_size = self.GetSize()
        make_window_transparent(self)
        self.canvas = parent.gl_canvas
        self.mouse_pos = wx.DefaultPosition
        self.start_pos = wx.DefaultPosition
        self.visualization = None
        self.width = 1
        self.height = 1
        self.dragging = False
        self.translucent_background = wx.Frame(
            parent, wx.ID_ANY, pos=self.GetScreenPosition(), size=self.GetSize(),
            style=wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT
        )

        self.translucent_background.SetTransparent(150)
        self.translucent_background.SetBackgroundColour(wx.BLACK)

        self.legend_image = StaticImage(self, wx.ID_ANY, Image.new("RGBA", self.GetSize().Get()))
        self.legend_image.SetSize(self.GetSize())
        self.legend_image.fit = False
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)
        main_sizer.Add(self.legend_image, 0, wx.EXPAND | wx.BOTTOM, 0)

        self.legend_image.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.legend_image.Bind(wx.EVT_MOTION, self.OnMotion)
        self.legend_image.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.legend_image.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnCaptureLost)
        self.legend_image.Bind(wx.EVT_RIGHT_DOWN, self.OnRightClick)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

        self.translucent_background.Bind(wx.EVT_LEFT_DOWN, self.OnBackgroundFocus)
        self.translucent_background.Bind(wx.EVT_RIGHT_DOWN, self.OnBackgroundFocus)

        parent = self.GetParent()
        while parent is not None:
            parent.Bind(wx.EVT_MOVE, self.OnMove)
            parent.Bind(wx.EVT_PAINT, self.OnPaintParent)
            parent = parent.GetParent()

        self.reset = True

    def OnBackgroundFocus(self, event: wx.MouseEvent):
        self.legend_image.SetFocus()
        wx.PostEvent(self.legend_image, event)

    def OnDestroy(self, event):
        parent = self.GetParent()
        while parent is not None:
            parent.Unbind(wx.EVT_MOVE)
            parent.Unbind(wx.EVT_PAINT)
            parent = parent.GetParent()
        event.Skip()

    def CalculateProportions(self):
        canvas_size = self.canvas.GetSize()
        size = self.GetSize()
        center = wx.Point(self.start_pos.x + size. x / 2, self.start_pos.y + size.y / 2)
        min_x = (size.x / 2) / canvas_size.x
        min_y = (size.y / 2) / canvas_size.y
        max_x = (canvas_size.x - size.x / 2) / canvas_size.x
        max_y = (canvas_size.y - size.y / 2) / canvas_size.y

        self.width = center.x / canvas_size.x
        if self.width <= min_x:
            self.width = 0.0
        elif self.width >= max_x:
            self.width = 1.0

        self.height = center.y / canvas_size.y
        if self.height <= min_y:
            self.height = 0.0
        elif self.height >= max_y:
            self.height = 1.0

    def RepaintLegend(self):
        canvas_pos = self.canvas.GetScreenPosition()
        canvas_size = self.canvas.GetSize()
        size = self.GetSize()

        if self.reset and self.IsShown():
            self.start_pos = wx.Point(0, canvas_size.y - size.y)
            self.CalculateProportions()
            self.reset = False

        x = canvas_pos.x + canvas_size.x * self.width - size.x / 2
        y = canvas_pos.y + canvas_size.y * self.height - size.y / 2

        if x < canvas_pos.x:
            x = canvas_pos.x
        elif x + size.x > canvas_pos.x + canvas_size.x:
            x = canvas_pos.x + canvas_size.x - size.x

        if y < canvas_pos.y:
            y = canvas_pos.y
        elif y + size.y > canvas_pos.y + canvas_size.y:
            y = canvas_pos.y + canvas_size.y - size.y

        new_pos = wx.Point(x, y)
        self.SetPosition(new_pos)
        self.translucent_background.SetPosition(new_pos)

        new_size = wx.Size(self.max_size)
        if canvas_size.x < self.max_size.x:
            new_size.SetWidth(canvas_size.x)
        if canvas_size.y < self.max_size.y:
            new_size.SetHeight(canvas_size.y)
        self.legend_image.SetSize(new_size)
        self.SetSize(new_size)
        self.translucent_background.SetSize(new_size)
        self.translucent_background.Refresh()
        self.legend_image.Refresh()

    def OnMove(self, event):
        self.RepaintLegend()
        event.Skip()

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self)
        dc.SetBackground(wx.Brush(wx.Colour(0, 0, 0), wx.BRUSHSTYLE_TRANSPARENT))
        dc.Clear()

        trans_dc = wx.BufferedPaintDC(self.translucent_background)
        trans_dc.Clear()
        trans_dc.SetBrush(wx.BLACK_BRUSH)
        trans_dc.DrawRectangle(0, 0, *self.GetSize().Get())

        self.RepaintLegend()
        event.Skip()

    def OnPaintParent(self, event):
        self.Refresh()
        event.Skip()

    def OnLeftDown(self, event):
        self.dragging = True
        self.legend_image.CaptureMouse()

    def OnMotion(self, event: wx.MouseEvent):
        canvas_pos = self.canvas.GetScreenPosition()
        canvas_size = self.canvas.GetSize()
        if self.dragging and event.LeftIsDown():
            if self.mouse_pos.x != -1 and self.mouse_pos.y != -1:
                pos = self.GetPosition()
                new_pos = wx.Point(pos.x + event.GetX() - self.mouse_pos.x, pos.y + event.GetY() - self.mouse_pos.y)
                size = self.GetSize()
                if new_pos.x < canvas_pos.x:
                    new_pos.x = canvas_pos.x
                if new_pos.y < canvas_pos.y:
                    new_pos.y = canvas_pos.y
                if new_pos.x + size.x > canvas_pos.x + canvas_size.x:
                    new_pos.x = canvas_pos.x + canvas_size.x - size.x
                if new_pos.y + size.y > canvas_pos.y + canvas_size.y:
                    new_pos.y = canvas_pos.y + canvas_size.y - size.y

                self.SetPosition(new_pos)
                self.translucent_background.SetPosition(new_pos)
            else:
                self.mouse_pos = event.GetPosition()
        else:
            self.mouse_pos = wx.DefaultPosition

    def OnLeftUp(self, event):
        if self.legend_image.HasCapture():
            self.dragging = False
            self.legend_image.ReleaseMouse()
            current_pos = self.GetPosition()
            canvas_pos = self.canvas.GetScreenPosition()
            self.start_pos = wx.Point(current_pos.x - canvas_pos.x, current_pos.y - canvas_pos.y)
            self.CalculateProportions()
            self.RepaintLegend()

    def OnCaptureLost(self, event):
        self.dragging = False

    def OnRightClick(self, event):
        menu = wx.Menu()
        menu.Append(self.RESET_LEGEND, "Reset Legend")
        menu.Bind(wx.EVT_MENU, self.OnPopupMenu)
        self.PopupMenu(menu, event.GetPosition())

    def OnPopupMenu(self, event: wx.MenuEvent):
        id = event.GetId()
        if id == self.RESET_LEGEND:
            self.reset = True
            self.RepaintLegend()

    def ShowWindow(self):
        self.mouse_pos = wx.DefaultPosition
        self.translucent_background.Show()
        self.Show()
        self.RepaintLegend()

    def HideWindow(self):
        self.translucent_background.Hide()
        self.Hide()

    def RefreshLegend(self):
        size = self.GetClientSize().Get()
        if self.visualization is not None and self.visualization.has_legend:
            self.legend_image.image = self.visualization.get_legend(*size)
        else:
            self.legend_image.image = Image.new("RGBA", size)
