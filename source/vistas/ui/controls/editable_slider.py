import wx
import wx.lib.newevent

EditableSliderEvent, EVT_SLIDER_CHANGE_EVENT = wx.lib.newevent.NewEvent()


class EditableSlider(wx.Panel):

    COMMIT_DELAY = 1500

    def __init__(self, parent, id, min_value=0, max_value=0, value=0):
        super().__init__(parent, id)

        self.timer = wx.Timer(self)
        self.slider = wx.Slider(self, wx.ID_ANY, 0, 0, 100)
        self.text = wx.TextCtrl(self, wx.ID_ANY, str(value), wx.DefaultPosition, wx.DefaultSize, wx.TE_PROCESS_ENTER)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(sizer)
        sizer.Add(self.slider, 1, wx.RIGHT, 5)
        sizer.Add(self.text)
        sizer.SetItemMinSize(self.text, wx.Size(70, -1))

        self._min_value = min_value
        self._max_value = max_value
        self._value = value

        self.Bind(wx.EVT_COMMAND_SCROLL, self.OnScroll)
        self.Bind(wx.EVT_TEXT, self.OnTextChange)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnTextEnter)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnLoseFocus)
        self.Bind(wx.EVT_TIMER, self.OnTimer)
        self._update_slider(value)

    def _update_slider(self, value, slider=True, text=True, send_event=False):
        if value < self._min_value:
            value = self._min_value
        elif value > self._max_value:
            value = self._max_value
        self._value = value

        if slider:
            self.slider.SetValue((value - self._min_value) * 100 / (self._max_value - self._min_value))

        if text:
            self.text.SetValue("{:.2f}".format(value))

        if send_event:
            evt = EditableSliderEvent()
            evt.SetEventObject(self)
            evt.value = value
            wx.PostEvent(self, evt)

    @property
    def min_value(self):
        return self._min_value

    @min_value.setter
    def min_value(self, value):
        self._min_value = value
        self._update_slider(self._value, True, False)

    @property
    def max_value(self):
        return self._max_value

    @max_value.setter
    def max_value(self, value):
        self._max_value = value
        self._update_slider(self._value, True, False)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._update_slider(value)

    def OnScroll(self, event):
        self.timer.Stop()
        self._update_slider(self.slider.GetValue() * (self._max_value - self._min_value) / 100 + self._min_value,
                            False, True, True)

    def OnTextChange(self, event):
        self.timer.Stop()
        self.timer.Start(self.COMMIT_DELAY, wx.TIMER_ONE_SHOT)

    def OnTextEnter(self, event):
        self.timer.Stop()
        self._update_slider(float(self.text.GetValue()), True, True, True)

    def OnLoseFocus(self, event):
        if event.GetEventObject() == self.text:
            self.timer.Stop()
            self._update_slider(float(self.text.GetValue()), True, True, True)

    def OnTimer(self, event):
        self._update_slider(float(self.text.GetValue()), True, True, True)
        self.timer.Stop()
