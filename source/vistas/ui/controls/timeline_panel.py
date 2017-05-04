import datetime

from vistas.core.utils import get_platform
from vistas.core.timeline import Timeline, EVT_TIMELINE_VALUE_CHANGED, EVT_TIMELINE_ATTR_CHANGED
from vistas.core.paths import get_resource_bitmap
from vistas.core.utils import get_paint_dc
from vistas.ui.controls.static_bitmap_button import StaticBitmapButton
from vistas.ui.controls.editable_slider import EditableSlider, EVT_SLIDER_CHANGE_EVENT

import wx


class PlaybackOptionsFrame(wx.Frame):

    def __init__(self, parent, id):
        super().__init__(parent, id, "Playback Options", style=wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT)
        self.SetSize(180, 95)

        timeline_panel = parent
        panel = wx.Panel(self, wx.ID_ANY)
        panel.SetSize(self.GetSize())
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self._live_update = wx.CheckBox(panel, wx.ID_ANY, "Live Update")
        self._show_every_frame = wx.CheckBox(panel, wx.ID_ANY, "Show Every Frame")
        self._uniform_time_intervals = wx.CheckBox(panel, wx.ID_ANY, "Uniform Time Intervals")
        label = wx.StaticText(panel, wx.ID_ANY, "Animation Speed")
        self._animation_slider = EditableSlider(panel, wx.ID_ANY, min_value=0.5, max_value=20.0, value=1.0)

        self._live_update.SetToolTip("Dragging the timeline cursor automatically updates the scene")
        self._show_every_frame.SetToolTip("Force the visualization to render every timestep (performace many be affected")
        self._uniform_time_intervals.SetToolTip("Display timestamps evenly on the timeline")

        panel.SetSizer(panel_sizer)
        panel_sizer.Add(label)
        panel_sizer.Add(self._animation_slider, 0, wx.EXPAND | wx.BOTTOM, 5)
        panel_sizer.Add(self._live_update, 0, wx.ALIGN_LEFT, 5)
        panel_sizer.AddSpacer(2)
        panel_sizer.Add(self._show_every_frame, 0, wx.ALIGN_LEFT, 5)
        panel_sizer.AddSpacer(2)
        panel_sizer.Add(self._uniform_time_intervals, 0, wx.ALIGN_LEFT, 5)

        self._animation_slider.Bind(EVT_SLIDER_CHANGE_EVENT, timeline_panel.OnAnimationSpeedSlider)
        self._live_update.Bind(wx.EVT_CHECKBOX, timeline_panel.OnLiveUpdate)
        self._show_every_frame.Bind(wx.EVT_CHECKBOX, timeline_panel.OnShowEveryFrame)
        self._uniform_time_intervals.Bind(wx.EVT_CHECKBOX, timeline_panel.OnUniformTimeIntervals)

        while parent is not None:
            parent.Bind(wx.EVT_MOVE, self.OnMove)
            parent.Bind(wx.EVT_PAINT, self.OnFramePaint)
            parent = parent.GetParent()

    @property
    def expanded(self):
        return self.IsShown()

    @property
    def animation_speed(self):
        return self._animation_slider.value

    @property
    def live_update(self):
        return self._live_update.GetValue()

    @property
    def show_every_frame(self):
        return self._show_every_frame.GetValue()

    @property
    def uniform_time_intervals(self):
        return self._uniform_time_intervals.GetValue()

    def Reposition(self):
        btn = self.GetParent().playback_options_button
        pos = btn.GetScreenPosition()
        btn_width, btn_height = btn.GetSize().Get()
        w, h = self.GetSize().Get()
        self.SetPosition(wx.Point(pos.x - w + btn_width, pos.y - h - btn_height / 2))

    def OnMove(self, event):
        self.Reposition()
        event.Skip()

    def OnFramePaint(self, event):
        self.Reposition()
        event.Skip()

    def ExpandOptions(self):
        self.SendSizeEvent()
        self.Show()

    def CollapseOptions(self):
        self.Hide()


class TimelineCtrl(wx.Control):

    CURSOR_WIDTH = 10
    HEIGHT = 10

    def __init__(self, parent, id, timeline=None):
        super().__init__(parent, id, style=wx.BORDER_NONE)

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

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnErase)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(EVT_TIMELINE_VALUE_CHANGED, self.OnValueChanged)
        self.Bind(EVT_TIMELINE_ATTR_CHANGED, self.OnAttrChanged)

    def _calculate_px_ratio(self):
        width = self.GetSize().x - self.CURSOR_WIDTH

        if not self.timeline.enabled:
            self.px_per_step = width
        elif self._uniform_time_intervals:
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
        dc = get_paint_dc(self)
        current = self.timeline.current_time
        start = self.timeline.start_time
        end = self.timeline.end_time
        min_step = self.timeline.min_step
        format = self.timeline.time_format

        w = self.GetSize().x - 1
        y_offset = dc.GetTextExtent(current.strftime(format)).y + 5

        dc.SetPen(wx.Pen(wx.BLACK, 1))
        dc.DrawRectangle(0, y_offset, w, self.HEIGHT)

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
        if get_platform() == 'windows':
            return
        event.Skip()

    def OnSize(self, event):
        dc = wx.WindowDC(self)

        text_size = dc.GetTextExtent(self.timeline.current_time.strftime(self.timeline.time_format))
        if self.timeline.enabled:
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


class TimelinePanel(wx.Panel):



    def __init__(self, parent, id):
        super().__init__(parent, id)
        self.SetMinSize(wx.Size(200, 40))

        self.timeline_ctrl = TimelineCtrl(self, wx.ID_ANY, Timeline.app())
        self.playback_options_frame = PlaybackOptionsFrame(self, wx.ID_ANY)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(sizer)

        self.step_to_beginning_button = wx.BitmapButton(
            self, wx.ID_ANY, bitmap=get_resource_bitmap('step_to_beginning_button.png')
        )
        self.step_backward_button = wx.BitmapButton(
            self, wx.ID_ANY, bitmap=get_resource_bitmap('step_backward_button.png')
        )
        self.play_button = wx.BitmapButton(
            self, wx.ID_ANY, bitmap=get_resource_bitmap('play_button.png')
        )
        self.step_forward_button = wx.BitmapButton(
            self, wx.ID_ANY, bitmap=get_resource_bitmap('step_forward_button.png')
        )
        self.step_to_end_button = wx.BitmapButton(
            self, wx.ID_ANY, bitmap=get_resource_bitmap('step_to_end_button.png')
        )
        self.playback_options_button = wx.BitmapButton(
            self, wx.ID_ANY, bitmap=get_resource_bitmap('playback_options_button.png')
        )

        # Todo: fix StaticBitmapButton
        #self.step_to_beginning_button = StaticBitmapButton(self, wx.ID_ANY, get_resource_bitmap('step_to_beginning_button.png'),
        #                                                   wx.DefaultPosition, wx.Size(20, 20))
        #self.step_backward_button = StaticBitmapButton(self, wx.ID_ANY, get_resource_bitmap('step_backward_button.png'),
        #                                                   wx.DefaultPosition, wx.Size(20, 20))
        #self.play_button = StaticBitmapButton(self, wx.ID_ANY, get_resource_bitmap('play_button.png'),
        #                                                   wx.DefaultPosition, wx.Size(20, 20))
        #self.step_forward_button = StaticBitmapButton(self, wx.ID_ANY, get_resource_bitmap('step_forward_button.png'),
        #                                                   wx.DefaultPosition, wx.Size(20, 20))
        #self.step_to_end_button = StaticBitmapButton(self, wx.ID_ANY, get_resource_bitmap('step_to_end_button.png'),
        #                                                   wx.DefaultPosition, wx.Size(20, 20))
        #self.playback_options_button = StaticBitmapButton(self, wx.ID_ANY, get_resource_bitmap('playback_options_button.png'),
        #                                                   wx.DefaultPosition, wx.Size(20, 20))

        # Todo: tooltips
        tooltips = ("Step to beginning",
                   "Step backward one frame",
                   "Play animation",
                   "Step forward one frame",
                   "Step to end",
                   "Expand playback options")

        sizer.Add(self.step_to_beginning_button, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        sizer.Add(self.step_backward_button, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        sizer.Add(self.play_button, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        sizer.Add(self.step_forward_button, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        sizer.Add(self.step_to_end_button, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        sizer.Add(self.timeline_ctrl, 1, wx.LEFT, 8)
        sizer.Add(self.playback_options_button, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, 5)

        self.play_bitmap = self.play_button.GetBitmap()
        self.pause_bitmap = get_resource_bitmap("pause_button.png")

        self.timer = wx.Timer(self, wx.ID_ANY)
        self._playing = False

        self.step_to_beginning_button.Bind(wx.EVT_BUTTON, self.OnStepToBeginningButton)
        self.step_backward_button.Bind(wx.EVT_BUTTON, self.OnStepBackwardButton)
        self.play_button.Bind(wx.EVT_BUTTON, self.OnPlayButton)
        self.step_forward_button.Bind(wx.EVT_BUTTON, self.OnStepForwardButton)
        self.step_to_end_button.Bind(wx.EVT_BUTTON, self.OnStepToEndButton)
        self.playback_options_button.Bind(wx.EVT_BUTTON, self.OnPlaybackOptionsButton)

        self.Bind(wx.EVT_TIMER, self.OnTimer)
        self.Fit()

    def _calc_frames_skipped(self, value):
        now = datetime.datetime.now()
        diff = self._last_frame - now
        if value < diff:
            return int(diff / value)
        else:
            return 0

    def OnStepToBeginningButton(self, event):
        if self.timeline_ctrl.timeline.enabled:
            self.timeline_ctrl.timeline.current_time = self.timeline_ctrl.timeline.start_time

    def OnStepBackwardButton(self, event):
        if self.timeline_ctrl.timeline.enabled and self.timeline_ctrl.timeline.current_index > 0:
            self.timeline_ctrl.timeline.back()

    def OnPlayButton(self, event):
        if self.timeline_ctrl.timeline.enabled:
            self._playing = not self._playing

            if self._playing and not self.timer.IsRunning():
                self.timer.Start(1, wx.TIMER_ONE_SHOT)
            elif self.timer.IsRunning():
                self.timer.Stop()

            if self._playing:
                bitmap = self.pause_bitmap
            else:
                bitmap = self.play_bitmap

            self.play_button.SetBitmap(bitmap)
        event.Skip()

    def OnStepForwardButton(self, event):
        if self.timeline_ctrl.timeline.enabled and \
                        self.timeline_ctrl.timeline.current_time < self.timeline_ctrl.timeline.end_time:
            self.timeline_ctrl.timeline.forward()

    def OnStepToEndButton(self, event):
        if self.timeline_ctrl.timeline.enabled:
            self.timeline_ctrl.timeline.current_time = self.timeline_ctrl.timeline.end_time

    def OnTimer(self, event):
        if self.timeline_ctrl.timeline.enabled and \
                        self.timeline_ctrl.timeline.current_time < self.timeline_ctrl.timeline.end_time:
            speed = 1000 / self.timeline_ctrl.animation_speed

            if self.timeline_ctrl.show_every_frame:
                self.timeline_ctrl.timeline.forward()
            else:
                self.timeline_ctrl.timeline.forward(1 + self._calc_frames_skipped(speed))
            self._last_frame = datetime.datetime.now()
            self.timer.Start(speed, wx.TIMER_ONE_SHOT)
        else:
            self._playing = False
            self.play_button.label_bitmap = self.play_bitmap

    def OnAnimationSpeedSlider(self, event):
        self.timeline_ctrl.animation_speed = self.playback_options_frame.animation_speed

    def OnPlaybackOptionsButton(self, event):
        if self.playback_options_frame.expanded:
            self.playback_options_frame.CollapseOptions()
        else:
            self.playback_options_frame.ExpandOptions()

    def OnLiveUpdate(self, event):
        self.timeline_ctrl.live_update = self.playback_options_frame.live_update

    def OnShowEveryFrame(self, event):
        self.timeline_ctrl.show_every_frame = self.playback_options_frame.show_every_frame

    def OnUniformTimeIntervals(self, event):
        self.timeline_ctrl.uniform_time_intervals = self.playback_options_frame.uniform_time_intervals
