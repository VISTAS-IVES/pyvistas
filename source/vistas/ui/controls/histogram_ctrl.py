from vistas.core.histogram import Histogram
from vistas.core.utils import get_paint_dc, get_platform

import wx
import wx.lib.newevent

HistogramCtrlValueChangedEvent, HISTOGRAM_CTRL_RANGE_VALUE_CHANGED_EVT = wx.lib.newevent.NewEvent()


class HistogramCtrl(wx.Control):

    HANDLE_WIDTH = 10
    HANDLE_HEIGHT = 10
    X_OFFSET = 5
    LABEL_PADDING = 5
    MIN_HANDLE = 0
    MAX_HANDLE = 1

    def __init__(self, parent, id, histogram=None):
        super().__init__(parent, id, style=wx.BORDER_NONE)
        if histogram is None:
            histogram = Histogram(None)
        self._dragging = False
        self.SetSize(1, 1)
        self.SetMinSize(wx.Size(0, 100))
        self.histogram = histogram
        self._px_per_value = None
        self.bins = None
        self.min_stop = None
        self.max_stop = None
        self.min_value = None
        self.max_value = None
        self.max_count = None
        self.RefreshBins()
        self.min_stop = self.min_value
        self.max_stop = self.max_value
        self.active_handle = self.MAX_HANDLE

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnCaptureLost)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
        if get_platform() == 'windows':
            self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnErase)
        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

        self.Refresh()

    def SetHistogram(self, histogram: Histogram, reset_stops=True):
        self.histogram = histogram
        self.RefreshBins()
        if reset_stops:
            self.min_stop = self.min_value
            self.max_stop = self.max_value
        else:
            self.min_stop = max(self.min_value, self.min_stop)
            self.max_stop = min(self.max_value, self.max_stop)
        self.Refresh()

    def SetStops(self, minimum, maximum):
        self.min_stop = max(self.min_value, min(minimum, maximum))
        self.max_stop = max(self.max_value, min(minimum, maximum))
        self.RefreshBins()
        self.Refresh()

    def OnPaint(self, event):
        dc = get_paint_dc(self)
        size = self.GetSize().Get()
        height = size[1] - self.HANDLE_HEIGHT - self.LABEL_PADDING - dc.GetTextExtent("0").GetHeight()
        height_factor = height / self.max_count
        min_pos = int((self.min_stop - self.min_value) * self._px_per_value)
        max_pos = int((self.max_stop - self.min_value) * self._px_per_value)
        length = self.bins.size

        if get_platform() == 'windows':
            win = self if self.UseBgCol() else self.GetParent()
            bg = win.GetBackgroundColour()
            scrim_color = wx.Colour(max(0, bg.Red()-50), max(0, bg.Green()-50), max(0, bg.Blue()-50))
        else:
            scrim_color = wx.Colour(0, 0, 0, 50)

        dc.SetBrush(wx.Brush(scrim_color))
        dc.SetPen(wx.Pen(scrim_color, 0))
        if min_pos > 0:
            dc.DrawRectangle(self.X_OFFSET, 0, min_pos, height)
        if max_pos < length:
            dc.DrawRectangle(max_pos + 1 + self.X_OFFSET, 0, length, height)

        def paint_lines(start, end):
            for i in range(start, end):
                dc.DrawLine(i + self.X_OFFSET, height, i + self.X_OFFSET, height - self.bins[i] * height_factor - 1)

        dc.SetPen(wx.GREY_PEN)
        paint_lines(0, min_pos)

        dc.SetPen(wx.BLACK_PEN)
        paint_lines(min_pos, max_pos)

        dc.SetPen(wx.GREY_PEN)
        paint_lines(max_pos+1, length)

        if self.min_stop > self.min_value + (self.max_value - self.min_value) / 2:
            right_edge = self.PaintHandle(dc, height, self.max_stop, -1, size[0]) - self.LABEL_PADDING
            self.PaintHandle(dc, height, self.min_stop, -1, right_edge)
        else:
            left_edge = self.PaintHandle(dc, height, self.min_stop, 0, -1) + self.LABEL_PADDING
            self.PaintHandle(dc, height, self.max_stop, left_edge, -1)

    def OnErase(self, event):
        return  # Prevent flickering on windows

    def OnSize(self, event):
        self.RefreshBins()
        self.Refresh()

    def OnLeftDown(self, event: wx.MouseEvent):
        dc = wx.MemoryDC()
        x = event.GetX()
        y = event.GetY()
        if y > self.GetSize().y - self.HANDLE_HEIGHT - self.LABEL_PADDING - dc.GetTextExtent("0").GetHeight():
            min_pos = (self.min_stop - self.min_value) * self._px_per_value
            max_pos = (self.max_stop - self.min_value) * self._px_per_value
            if abs(x - min_pos) < abs(x - max_pos):
                self.active_handle = self.MIN_HANDLE
            else:
                self.active_handle = self.MAX_HANDLE
            self._dragging = True
            self.CaptureMouse()

    def OnLeftUp(self, event):
        self._dragging = False
        if self.HasCapture():
            self.ReleaseMouse()

    def OnMouseMove(self, event: wx.MouseEvent):
        if self._dragging and event.LeftIsDown():
            value = event.GetX() / self._px_per_value + self.min_value
            if self.active_handle == self.MIN_HANDLE:
                self.min_stop = max(self.min_value, min(value, self.max_stop))
            else:
                self.max_stop = min(self.max_value, max(value, self.min_stop))
            wx.PostEvent(self, HistogramCtrlValueChangedEvent(min_stop=self.min_stop, max_stop=self.max_stop))
            self.Refresh()

    def OnCaptureLost(self, event):
        self._dragging = False

    def OnMouseEnter(self, event):
        if not event.LeftIsDown():
            self._dragging = False

    def HasTransparentBackground(self):
        return True

    def PaintHandle(self, dc: wx.DC, y_offset, value, left_edge, right_edge):
        pos = (value - self.min_value) * self._px_per_value + self.X_OFFSET
        dc.SetBrush(wx.BLACK_BRUSH)
        dc.DrawPolygon((
            wx.Point(pos, y_offset),
            wx.Point(pos - self.HANDLE_WIDTH / 2, y_offset + self.HANDLE_HEIGHT),
            wx.Point(pos + self.HANDLE_WIDTH / 2, y_offset + self.HANDLE_HEIGHT),
        ))

        label = "{:.3f}".format(value)
        label_width = dc.GetTextExtent(label).GetWidth()
        label_pos = pos - label_width / 2
        width = self.GetSize().x
        label_pos = max(min(width - label_width, label_pos), 0)

        if left_edge != -1:
            label_pos = max(left_edge, label_pos)
            edge = label_pos + label_width
        elif right_edge != -1:
            label_pos = min(right_edge, - label_width, label_pos)
            edge = label_pos

        dc.DrawText(label, label_pos, y_offset + self.HANDLE_HEIGHT + self.LABEL_PADDING)
        return edge

    def RefreshBins(self):
        width = self.GetSize().x
        self.bins = self.histogram.generate_histogram(width)
        print(self.bins)
        self.max_count = self.bins.size
        self.min_value = self.bins.min()
        self.max_value = self.bins.max()
        if self.min_value != self.max_value:
            self._px_per_value = (width - self.HANDLE_WIDTH) / (self.max_value - self.min_value)
        else:
            self._px_per_value = 1
