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
        self._current_bitmap = None
        self._label_bitmap = label
        self._disabled_bitmap = None
        self._hover_bitmap = None
        self._selected_bitmap = None
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

        # trigger update
        self.label_bitmap = label

    def update(self, setter_func):
        def wrap(*args, **kwargs):
            # Apply function
            setter_func(*args, **kwargs)

            # update the current bitmap
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
        return wrap

    @property
    def disabled_bitmap(self):
        return self._disabled_bitmap

    @update
    @disabled_bitmap.setter
    def disabled_bitmap(self, value):
        self._disabled_bitmap = value

    @property
    def hover_bitmap(self):
        return self._hover_bitmap

    @update
    @hover_bitmap.setter
    def hover_bitmap(self, value):
        self._hover_bitmap = value

    @property
    def label_bitmap(self):
        return self._label_bitmap

    @update
    @label_bitmap.setter
    def label_bitmap(self, value):
        self._label_bitmap = value

    @property
    def selected_bitmap(self):
        return self._selected_bitmap

    @update
    @selected_bitmap.setter
    def selected_bitmap(self, value):
        self._selected_bitmap = value

    def OnPaint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.DrawBitmap(self._current_bitmap, 1, 1, True)

    @update
    def OnMouseEnter(self, event):
        if not self.IsEnabled():
            return
        self._hover = True
        if not event.LeftIsDown():
            self._click = False

    @update
    def OnMouseLeave(self, event):
        self._hover = False

    @update
    def OnLeftDown(self, event):
        self._click = False

    @update
    def OnLeftUp(self, event):
        if self._click:
            evt = wx.CommandEvent(wx.EVT_BUTTON)
            evt.SetEventObject(self)
            wx.PostEvent(self, evt)
        self._click = False
