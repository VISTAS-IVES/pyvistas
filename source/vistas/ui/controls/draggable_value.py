from vistas.core.utils import get_transparent_paint_dc

import wx
import wx.lib.newevent

DraggableValueEvent, EVT_DRAG_VALUE_EVENT = wx.lib.newevent.NewEvent()


class DraggableValue(wx.Window):
    def __init__(self, parent, id, value, per_px):
        super().__init__(parent, id)

        self._value = value
        self._per_px = per_px
        self._dragging = False
        self._mouse_pos = None

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        extent = wx.ClientDC(self).GetTextExtent("{:.2f}".format(self._value))
        self.SetMinSize(wx.Size(extent.x, extent.y + 1))
        self.GetParent().Layout()
        self.Refresh()

    def OnPaint(self, event):
        dc = get_transparent_paint_dc(self)
        dc.SetTextForeground(wx.Colour(0, 0, 255))
        dc.SetPen(wx.Pen(wx.Colour(0, 0, 255), 1, wx.DOT))
        dc.DrawText("{:.2f}".format(self._value))
        width, height = self.GetSize().Get()
        dc.DrawLine(0, height - 2, width, height - 2)

    def OnLeftDown(self, event):
        self.CaptureMouse()
        self._dragging = True
        self._mouse_pos = event.GetPosition()

    def OnLeftUp(self, event):
        if self.HasCapture():
            self.ReleaseMouse()
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))
            self._dragging = False

    def OnCaptureLost(self, event):
        self.ReleaseMouse()
        self.SetCursor((wx.Cursor(wx.CURSOR_SIZEWE)))
        self._dragging = False

    def OnMotion(self, event):
        if self._dragging or not event.LeftIsDown():
            return

        current_mouse_pos = event.GetPosition()

        # intentional use of value.setter
        self.value = current_mouse_pos.x - self._mouse_pos.x * self._per_px
        self._mouse_pos = current_mouse_pos

        evt = DraggableValueEvent()
        wx.PostEvent(self, evt)
