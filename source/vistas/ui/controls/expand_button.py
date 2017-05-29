from vistas.core.utils import get_paint_dc

import wx


class ExpandButton(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent, wx.ID_ANY)
        self.SetPosition(wx.Point(0, 50))
        self.SetSize(wx.Size(20, 20))
        self.frame = wx.Frame(wx.GetTopLevelParent(self),
                              style=wx.CLIP_CHILDREN | wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT | wx.BORDER_NONE)
        self._alpha = 50
        self.frame.SetTransparent(self._alpha)
        self.frame.SetSize(wx.Size(20, 20))
        self.frame.SetPosition(self.GetScreenPosition())
        self.frame.Show()
        self.frame.Bind(wx.EVT_PAINT, self.OnPaint)
        self.frame.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
        self.frame.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self.frame.Bind(wx.EVT_LEFT_DOWN, self.OnClick)
        self.Bind(wx.EVT_MOVE, self.OnMove)
        while parent is not None:
            parent.Bind(wx.EVT_MOVE, self.OnMove)
            parent = parent.GetParent()

        self._expanded = True

    @property
    def expanded(self):
        return self._expanded

    @expanded.setter
    def expanded(self, value):
        self._expanded = value
        self.frame.Refresh()

    @property
    def alpha(self):
        return self._alpha

    @alpha.setter
    def alpha(self, value):
        self._alpha = value
        self.Refresh()

    def OnClick(self, event):
        wx.PostEvent(self, event)

    def OnMove(self, event):
        self.frame.SetPosition(self.GetScreenPosition())
        event.Skip()

    def OnPaint(self, event):

        dc = get_paint_dc(self.frame)
        dc.Clear()
        dc.SetBrush(wx.Brush(wx.Colour(221, 221, 221)))
        dc.SetPen(wx.Pen(wx.Colour(211, 211, 211)))
        dc.DrawRectangle(0, 0, 16, 20)
        dc.DrawRoundedRectangle(0, 0, 20, 20, 4)

        if self._expanded:
            points = [
                wx.Point(5, 10),
                wx.Point(15, 17),
                wx.Point(15, 3)
            ]

        else:
            points = [
                wx.Point(5, 3),
                wx.Point(5, 17),
                wx.Point(15, 10)
            ]

        dc.SetBrush(wx.BLACK_BRUSH)
        dc.SetPen(wx.BLACK_PEN)
        dc.DrawPolygon(points)
        self.frame.SetTransparent(self._alpha)

    def OnEnter(self, event):
        self._alpha = 200
        self.frame.Refresh()

    def OnLeave(self, event):
        self._alpha = 50
        self.frame.Refresh()
