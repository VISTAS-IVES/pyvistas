import datetime
import time

import wx


class TaskDialog(wx.Dialog):
    def __init__(self, parent, task, show_timer=False, allow_cancel=False):
        super().__init__(parent, wx.ID_ANY, 'Status', style=wx.SYSTEM_MENU | wx.CAPTION)

        self.SetMinSize((300, -1))

        self.task = task
        self.timer = wx.Timer()
        self.show_timer = show_timer

        main_panel = wx.Panel(self, wx.ID_ANY)
        box = wx.StaticBox(main_panel, wx.ID_ANY, 'Status')
        self.status_static = wx.StaticText(main_panel, wx.ID_ANY, 'Please wait...')
        self.gauge = wx.Gauge(main_panel, wx.ID_ANY, 100)

        if show_timer:
            self.timer_static = wx.StaticText(main_panel, wx.ID_ANY, 'Stopped.')

        if allow_cancel:
            cancel_button = wx.Button(main_panel, wx.ID_ANY, 'Cancel')
            cancel_button.Bind(wx.EVT_BUTTON, self.OnCancel)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)

        main_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        main_panel.SetSizer(main_panel_sizer)

        box_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        box_sizer.Add(self.status_static, 0, wx.BOTTOM, 5)
        box_sizer.Add(self.gauge, 0, wx.EXPAND)

        if show_timer:
            box_sizer.Add(self.timer_static, 0, wx.TOP | wx.EXPAND, 5)

        main_panel_sizer.Add(box_sizer, 1, wx.EXPAND | wx.ALL, 10)

        if allow_cancel:
            main_panel_sizer.Add(cancel_button, 0, wx.ALIGN_RIGHT | wx.RIGHT, 10)
            main_panel_sizer.AddSpacer(10)

        main_sizer.Add(main_panel, 1, wx.EXPAND)

        if parent is not None:
            self.CenterOnParent()
        else:
            self.CenterOnScreen()

        self.Layout()
        self.Fit()

        self.timer.Bind(wx.EVT_TIMER, self.OnTimer)

        self.start_time = time.time()
        self.timer.Start(100, False)

    def OnTimer(self, event):
        if self.task.stopped or self.task.complete:
            self.timer.Stop()

            if self.IsModal():
                self.EndModal(0)

            self.Destroy()
            return

        if self.task.indeterminate:
            self.gauge.Pulse()

        elif self.task.percent > 0:
            self.gauge.SetValue(self.task.percent)

            if self.show_timer:
                elapsed_seconds = round(time.time() - self.start_time)
                hours = elapsed_seconds // 3600
                minutes = (elapsed_seconds % 3600) // 60
                seconds = elapsed_seconds % 3600 % 60
                elapsed_time = datetime.time(hours, minutes, seconds)
                progress = self.gauge.GetValue()

                elapsed = elapsed_time.strftime('%H:%M:%S')

                if progress == 0 or elapsed_seconds < 5:
                    est_seconds = -1
                else:
                    est_seconds = round((elapsed_seconds / progress) * (100 - progress))
                    hours = est_seconds // 3600
                    minutes = (est_seconds % 3600) // 60
                    seconds = est_seconds % 3600 % 60

                if est_seconds < 0:
                    estimate = 'calculating...'

                elif est_seconds < 60:
                    estimate = 'less than a minute'

                elif 90 > est_seconds >= 60:
                    estimate = 'about one minute'

                elif hours > 0:
                    if minutes >= 30:
                        hours += 1

                    estimate = 'about one hour' if hours < 2 else 'about {} hours'.format(hours)

                else:
                    if seconds >= 30:
                        minutes += 1

                    estimate = 'about {} minutes'.format(minutes)

                self.timer_static.SetLabel('Elapsed Time: {}\nRemaining Time: {}'.format(elapsed, estimate))

        if self.task.description is not None and self.status_static.GetLabel() != self.task.description:
            self.status_static.SetLabel(self.task.description)

    def OnCancel(self, event):
        self.task.status = self.task.SHOULD_STOP
        self.Hide()
