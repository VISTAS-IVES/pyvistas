from vistas.core.timeline import Timeline, EVT_TIMELINE_ATTR_CHANGED, EVT_TIMELINE_VALUE_CHANGED

import wx


class TimelineCtrl(wx.Control):

    CURSOR_WIDTH = 10
    HEIGHT = 10

    def __init__(self, parent, id, timeline=None):
        super().__init__(parent, id)
        self.SetWindowStyle(wx.BORDER_NONE)

        if timeline is None:
            timeline = Timeline.app()

        self.timeline = timeline
        self._scrub_time = None
        self.animation_speed = 1
        self.live_update = False
        self.show_every_frame = False
        self._uniform_time_intervals = False
        self._dragging = False
        self.px_per_step = None
        self._calculate_px_ratio()

    def _calculate_px_ratio(self):
        width = self.GetSize().x - self.CURSOR_WIDTH
        if self._uniform_time_intervals:
            self.px_per_step = width / (self.timeline.num_timestamps - 1)
        else:
            self.px_per_step = width / ((self.timeline.end_time - self.timeline.start_time) / self.timeline.min_step)

    @property
    def uniform_time_intervals(self):
        return self._uniform_time_intervals

    @uniform_time_intervals.setter
    def uniform_time_intervals(self, value):
        self._uniform_time_intervals = value
        self._calculate_px_ratio()
        self.Refresh()

    def time_at_position(self, pos):
        timestamps = self.timeline.timestamps
        width = self.GetSize().x - self.CURSOR_WIDTH
        start = timestamps[0]
        end = timestamps[-1]
        prev = end
        for t in timestamps:
            if t == start:
                continue

            # get the split point between prev and t, and determine pixel position
            diff = (t - prev) / (end - start) / 2
            point = round(width * (((t - start) / (end - start)) - diff))
            if pos <= point:
                return prev

            prev = t

        # always return end for edge case
        return end

    def OnPaint(self, event):

        dc = wx.AutoBufferedPaintDC(self)

        current = self.timeline.current_time
        start = self.timeline.start_time
        end = self.timeline.end_time
        min_step = self.timeline.min_step
        format = "%H:%M:%S" # Todo: implment timeline.time_format

        w = self.GetSize().x - 1
        y_offset = dc.GetTextExtent(current.strftime(format)).y = 5

        dc.SetPen(wx.Pen(wx.BLACK, 1))
        dc.DrawLine(0, y_offset, w, y_offset)
        dc.DrawLine(0, y_offset + self.HEIGHT, w, y_offset + self.HEIGHT)
        dc.DrawLine(0, y_offset, 0, y_offset + self.HEIGHT)
        dc.DrawLine(w, y_offset, w, y_offset + self.HEIGHT)

        if start == end:
            return

        def draw_polygon(position):
            dc.DrawPolygon(
                (wx.Point(position, y_offset),
                 wx.Point(position - self.CURSOR_WIDTH / 2, y_offset + self.CURSOR_WIDTH / 2),
                 wx.Point(position, y_offset + self.CURSOR_WIDTH),
                 wx.Point(position + self.CURSOR_WIDTH / 2, y_offset + self.CURSOR_WIDTH / 2)
                 )
            )

        dc.DrawText(start.strftime(format), 0, 0)
        dc.DrawText(end.strftime(format), w - dc.GetTextExtent(end.strftime(format)).x, 0)
        dc.DrawText(current.strftime(format), w / 2 - dc.GetTextExtent(current.strftime(format)) / 2, 0)

        if self._uniform_time_intervals:
            numsteps = self.timeline.current_index
        else:
            numsteps = round((current - start) / min_step)
        pos = self.CURSOR_WIDTH / 2 + numsteps * self.px_per_step

        dc.SetBrush(wx.BLACK_BRUSH)
        draw_polygon(pos)

        if self._dragging and self._scrub_time != current:
            if self._uniform_time_intervals:
                numsteps = self.timeline.index_at_time(self._scrub_time)
            else:
                numsteps = round((self._scrub_time - start) / min_step)
            pos = self.CURSOR_WIDTH / 2 + numsteps * self.px_per_step
            dc.SetBrush(wx.Brush(wx.Colour(55, 55, 55)))
            dc.SetPen(wx.Pen(wx.Colour(55, 55, 55)))
            draw_polygon(pos)

            tip_extent = dc.GetTextExtent(self._scrub_time.strftime(format))

            if pos > w / 2:
                tip = wx.Point(pos - tip_extent.x - self.CURSOR_WIDTH / 2 - 11, 2).Get()
            else:
                tip = wx.Point(pos + self.CURSOR_WIDTH / 2 + 5, 2).Get()

            dc.SetPen(wx.BLACK_PEN)
            dc.SetBrush(wx.Colour(255, 255, 179))

            dc.DrawRectangle(tip[0], tip[1], tip_extent.x + 6, tip_extent.y + 2)
            dc.DrawText(self._scrub_time.strftime(format), tip[0] + 3, tip[1] + 1)

    def OnErase(self, event):
        pass    # Todo: is this needed anymore?

    def OnSize(self, event):
        dc = wx.WindowDC(self)

        # Todo: format = self.timeline.time_format (Implement self.timeline.time_format as a property)
        text_size = dc.GetTextExtent(self.timeline.current_time.strftime("%H:%M:%S"))
        if self.timeline.start_time == self.timeline.end_time:
            self.SetMinSize(wx.Size(0, self.HEIGHT + 5 + text_size.y + 5))
        else:
            self.SetMinSize(wx.Size(text_size.x * 3 + 15, self.HEIGHT + 5 + text_size.y + 5))

        self._calculate_px_ratio()
        self.Refresh()

    def OnLeftDown(self, event):
        if self.timeline.start_time == self.timeline.end_time:
            return

        self._dragging = True
        self._scrub_time = self.timeline.current_time
        self.CaptureMouse()

    def OnLeftUp(self, event):
        if self.timeline.start_time == self.timeline.end_time:
            return

        if self.HasCapture():
            if self._dragging and self._scrub_time != self.timeline.current_time:
                self.timeline.current_time = self._scrub_time
                # Todo: TimelineCtrlEvent?

            self._dragging = False
            self.ReleaseMouse()
            self.Refresh()

    def OnMouseMove(self, event):
        if self.timeline.start_time == self.timeline.end_time:
            return

        if self._dragging and event.LeftIsDown():
            if self._uniform_time_intervals:
                t = self.timeline.time_at_index(round(event.GetPosition().x / self.px_per_step))
            else:
                t = self.timeline

    def OnLoseCapture(self, event):
        self._dragging = False

    def OnMouseEnter(self, event):
        self._dragging = event.LeftIsDown()

    def OnValueChanged(self, event):
        self._calculate_px_ratio()
        self.Refresh()

    def OnAttrChanged(self, event):
        self._calculate_px_ratio()
        self.Refresh()
