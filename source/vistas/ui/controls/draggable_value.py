from vistas.core.utils import get_paint_dc

import wx
import wx.lib.newevent

DraggableValueEventBase, EVT_DRAG_VALUE_EVENT = wx.lib.newevent.NewEvent()


class DraggableValueEvent(DraggableValueEventBase):
    def __init__(self, value):
        super().__init__(value=value)


class DraggableValue(wx.Window):
    def __init__(self, parent, id, value, per_px):
        super().__init__(parent, id)

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self._value = None
        self._per_px = per_px
        self._dragging = False
        self._mouse_pos = None
        self.value = value
        self._temp_value = 0
        self.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOTION, self.OnMotion)

    def _repaint(self):
        extent = wx.ClientDC(self).GetTextExtent("{:.2f}".format(self._value))
        self.SetMinSize(wx.Size(extent.x, extent.y + 1))
        self.GetParent().Layout()
        self.Refresh()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        self._repaint()

    def OnPaint(self, event):
        dc = get_paint_dc(self)
        dc.SetTextForeground(wx.Colour(0, 0, 255))
        dc.SetPen(wx.Pen(wx.Colour(0, 0, 255), 1, wx.DOT))
        value = self._value if not self._dragging else self._temp_value
        dc.DrawText("{:.2f}".format(value), 0, 0)
        width, height = self.GetSize().Get()
        dc.DrawLine(0, height - 2, width, height - 2)

    def OnLeftDown(self, event):
        self.CaptureMouse()
        self._dragging = True
        self._mouse_pos = event.GetPosition()
        self._temp_value = 0

    def OnLeftUp(self, event):
        if self.HasCapture():
            self.ReleaseMouse()
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))
            self._dragging = False
            self.value = self._temp_value
            self._temp_value = 0

    def OnCaptureLost(self, event):
        self.ReleaseMouse()
        self.SetCursor((wx.Cursor(wx.CURSOR_SIZEWE)))
        self._dragging = False
        self.value = self._temp_value
        self._temp_value = 0

    def OnMotion(self, event):
        if not self._dragging or not event.LeftIsDown():
            return

        current_mouse_pos = event.GetPosition()
        self._temp_value = self.value + current_mouse_pos.x - self._mouse_pos.x * self._per_px
        self._mouse_pos = current_mouse_pos
        self._repaint()

        evt = DraggableValueEvent(value=self.value)
        wx.PostEvent(self, evt)
