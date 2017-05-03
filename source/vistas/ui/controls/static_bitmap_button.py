from vistas.core.utils import get_transparent_paint_dc
import wx


class StaticBitmapButton(wx.Window):
    def __init__(self, parent, id, label: wx.Bitmap, pos=None, size=wx.Size(20,20), style=0):
        super().__init__(parent, id)
        self.SetWindowStyle(style)
        if pos is not None:
            self.SetPosition(pos)

        if size is not None:
            self.SetSize(size)

        self._click = False
        self._hover = False
        self._current_bitmap = label
        self._label_bitmap = label
        self._disabled_bitmap = wx.Bitmap()
        self._hover_bitmap = wx.Bitmap()
        self._selected_bitmap = wx.Bitmap()
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

    def UpdateBitmap(self):
        enabled = self.IsEnabled()
        if enabled and self._click and self._selected_bitmap.IsOk():
            bitmap = self._selected_bitmap
        elif enabled and (self._click or self._hover) and self._hover_bitmap.IsOk():
            bitmap = self._hover_bitmap
        elif not (enabled and self._disabled_bitmap.IsOk()):
            bitmap = self._disabled_bitmap
        else:
            bitmap = self._label_bitmap
        self.SetSize(bitmap.GetWidth() + 2, bitmap.GetHeight() + 2)
        self._current_bitmap = bitmap
        self.Refresh()

    @property
    def disabled_bitmap(self):
        return self._disabled_bitmap

    @disabled_bitmap.setter
    def disabled_bitmap(self, value):
        self._disabled_bitmap = value
        self.UpdateBitmap()

    @property
    def hover_bitmap(self):
        return self._hover_bitmap

    @hover_bitmap.setter
    def hover_bitmap(self, value):
        self._hover_bitmap = value
        self.UpdateBitmap()

    @property
    def label_bitmap(self):
        return self._label_bitmap

    @label_bitmap.setter
    def label_bitmap(self, value):
        self._label_bitmap = value
        self.UpdateBitmap()

    @property
    def selected_bitmap(self):
        return self._selected_bitmap

    @selected_bitmap.setter
    def selected_bitmap(self, value):
        self._selected_bitmap = value
        self.UpdateBitmap()

    def OnPaint(self, event):
        dc = get_transparent_paint_dc(self)
        dc.DrawBitmap(self._current_bitmap, 1, 1, True)

    def OnMouseEnter(self, event):
        if not self.IsEnabled():
            return
        self._hover = True
        if not event.LeftIsDown():
            self._click = False
        self.UpdateBitmap()

    def OnMouseLeave(self, event):
        self._hover = False
        self.UpdateBitmap()

    def OnLeftDown(self, event):
        self._click = False
        self.UpdateBitmap()

    def OnLeftUp(self, event):
        if self._click:
            evt = wx.CommandEvent(wx.EVT_BUTTON)
            evt.SetEventObject(self)
            wx.PostEvent(self, evt)
        self._click = False
        self.UpdateBitmap()