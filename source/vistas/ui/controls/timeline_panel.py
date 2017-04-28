from vistas.core.timeline import Timeline

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
        pass

    def OnErase(self, event):
        pass    # Todo: is this needed anymore?

    def OnSize(self, event):
        pass

    def OnLeftDown(self, event):
        pass

    def OnLeftUp(self, event):
        pass

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
