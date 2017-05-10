import bisect
from datetime import time
import wx
import wx.lib.newevent

KeyframeTimelineSelectEvent, EVT_KEYTIMELINE_SEL = wx.lib.newevent.NewEvent()
KeyframeTimelineDeleteEvent, EVT_KEYTIMELINE_DEL = wx.lib.newevent.NewEvent()
KeyframeTimelineUpdateEvent, EVT_KEYTIMELINE_UPDATE = wx.lib.newevent.NewEvent()


class KeyframeTimeline(wx.Window):

    CURSOR_WIDTH = 10

    def __init__(self, parent, id, num_keyframes, fps):
        super().__init__(parent, id)
        self._max_frame = num_keyframes
        self._current_frame = 0
        self.fps = fps
        self._selected_keyframe = None
        self.SetSize(-1, 29)
        self._dragging = False
        self._scrub_frame = None
        self._keyframes = []

    @property
    def px_ratio(self):
        return (self.GetSize().x - self.CURSOR_WIDTH) / self._max_frame

    @property
    def max_frame(self):
        return self._max_frame

    @max_frame.setter
    def max_frame(self, value):
        self._max_frame = value
        self.Refresh()

    @property
    def current_frame(self):
        return self._current_frame

    @current_frame.setter
    def current_frame(self, value):
        self._current_frame = value
        self.Refresh()

    @property
    def keyframes(self):
        return self._keyframes

    @keyframes.setter
    def keyframes(self, value):
        self._keyframes = value
        self.Refresh()

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self, self.buffer)
        fmt = "%M:%S"
        start = time(second=0).strftime(fmt)
        end = time(second=self._max_frame / self.fps).strftime(fmt)
        current = time(second=self._current_frame / self.fps).strftime(fmt)

        size = self.GetSize()
        y_offset = dc.GetTextExtent(start).y + 2
        x_offset = size.x - 1

        dc.SetPen(wx.Pen(wx.Colour(0, 0, 0)))
        dc.DrawLine(0, y_offset, x_offset, y_offset)
        dc.DrawLine(0, size.y - 1, x_offset, size.y - 1)
        dc.DrawLine(0, y_offset, 0, size.y - 1)
        dc.DrawLine(size.x - 1, y_offset, size.x - 1, size.y - 1)

        dc.SetBrush(wx.Brush(wx.Colour(0, 0, 0)))

        dc.DrawText(start, 0, 0)
        dc.DrawText(end, x_offset - dc.GetTextExtent(end).x, 0)
        dc.DrawText(current, (size.x - 1) / 2 - dc.GetTextExtent(current).x / 2, 0)

        cw = self.CURSOR_WIDTH / 2
        px_ratio = self.px_ratio

        # Draw keyframes
        for frame in self._keyframes:
            midpoint = frame * px_ratio + cw
            if frame == self._selected_keyframe:
                dc.SetBrush(wx.Brush(wx.Colour(255, 255, 0)))
            else:
                dc.SetBrush(wx.Brush(wx.Colour(0, 128, 192)))
            dc.DrawPolygon((
                wx.Point(midpoint, y_offset),
                wx.Point(midpoint + cw, cw + y_offset),
                wx.Point(midpoint, self.CURSOR_WIDTH + y_offset),
                wx.Point(midpoint - cw, cw + y_offset)
            ))

        # Draw cursor
        dc.SetBrush(wx.Brush(wx.BLACK_BRUSH))
        pos = self._current_frame * px_ratio + cw
        dc.DrawPolygon((
            wx.Point(pos, y_offset),
            wx.Point(pos + cw, cw + y_offset),
            wx.Point(pos, self.CURSOR_WIDTH + y_offset),
            wx.Point(pos - cw, cw + y_offset)
        ))

        # Draw scrub cursor
        if self._dragging and self._scrub_frame != self._current_frame:
            midpoint = self._scrub_frame * px_ratio + cw
            if self._selected_keyframe is not None:
                dc.SetBrush(wx.Brush(wx.Colour(0, 128, 192)))
            else:
                dc.SetBrush(wx.Brush(wx.Colour(55, 55, 55)))
            dc.SetPen(wx.Pen(wx.Colour(55, 55, 55)))
            dc.DrawPolygon((
                wx.Point(midpoint, y_offset),
                wx.Point(midpoint + cw, cw + y_offset),
                wx.Point(midpoint, self.CURSOR_WIDTH + y_offset),
                wx.Point(midpoint - cw, cw + y_offset)
            ))

    def OnLeftDown(self, event):
        x = event.GetPosition().x
        self.SetFocus()
        cw = self.CURSOR_WIDTH / 2
        for frame in self._keyframes:
            midpoint = frame * self.px_ratio + cw
            if midpoint - cw <= x <= midpoint + cw:
                self._selected_keyframe = frame
                break
            else:
                self._selected_keyframe = None
        self.CaptureMouse()
        self._dragging = True
        self._scrub_frame = self._current_frame
        self.Refresh()

    def OnLeftDoubleClick(self, event):
        if self._selected_keyframe is not None:
            self._current_frame = self._selected_keyframe
            evt = KeyframeTimelineSelectEvent()
            evt.frame = self._current_frame
            evt.SetEventObject(self)
            wx.PostEvent(self, evt)
            self.Refresh()

    def OnLeftUp(self, event):
        if self.HasCapture():
            if self._dragging and self._scrub_frame != self._current_frame:
                self._selected_keyframe = self._scrub_frame
                evt = KeyframeTimelineUpdateEvent()
                evt.frame = self._selected_keyframe
                evt.scrub_frame = self._scrub_frame
            else:
                self._current_frame = self._current_frame
                evt = KeyframeTimelineSelectEvent()
                evt.frame = self._current_frame
            evt.SetEventObject(self)
            wx.PostEvent(self, evt)
            self._dragging = False
            self.ReleaseMouse()

    def OnRightClick(self, event):
        if event.RightIsDown():
            cw = self.CURSOR_WIDTH / 2
            for frame in self._keyframes:
                midpoint = frame * self.px_ratio + cw
                if midpoint - cw <= event.GetPosition().x <= midpoint + cw:
                    self._selected_keyframe = frame
                    break
                else:
                    self._selected_keyframe = None
            self.Refresh()
            if self._selected_keyframe is not None:
                pass    # Todo: create popup menu for deleting keyframes

    def OnPopupMenu(self, event):
        pass    # Todo: create popup menu for deleting keyframes

    def OnMouseMove(self, event):
        if self._dragging and event.LeftIsDown():
            scrub_frame = event.GetPosition().x / self.px_ratio

            if scrub_frame > self._max_frame:
                scrub_frame = self._max_frame
            elif scrub_frame < 0:
                scrub_frame = 0

            if scrub_frame != self._scrub_frame:
                self._scrub_frame = scrub_frame
                if self._selected_keyframe is None:
                    evt = KeyframeTimelineSelectEvent()
                    evt.SetEventObject(self)
                    wx.PostEvent(self, evt)
                self.Refresh()

    def OnKeyDown(self, event):
        key = event.GetKeyCode()

        if self._selected_keyframe is not None and key in [wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE, wx.WXK_BACK]:
            self.RemoveKeyframe(self._selected_keyframe)
            self.Refresh()

            evt = KeyframeTimelineDeleteEvent()
            evt.frame = self._selected_keyframe
            evt.SetEventObject(self)
            wx.PostEvent(self, evt)

            self._selected_keyframe = None

    def OnErase(self, event):
        return  # Prevent flickering on Windows

    def AddKeyframe(self, frame):
        bisect.insort(self._keyframes, frame)
        self.Refresh()

    def RemoveKeyframe(self, frame):
        if frame in self._keyframes:
            self._keyframes.remove(frame)

    def Clear(self):
        self._keyframes = []
        self.Refresh()
