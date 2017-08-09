import wx

from vistas.core.task import Task


class MainStatusBar(wx.StatusBar):
    """ Main task status bar for currently running Tasks. """

    def __init__(self, parent, id):
        super().__init__(parent, id)
        self.SetFieldsCount(2, [70, -1])
        self.SetStatusText("Idle", 1)
        self.gauge = None
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnNotify)
        self.timer.Start(100, True)

    def OnNotify(self, event):
        task = Task.tasks[-1] if len(Task.tasks) else None
        if task is not None and task.status not in [Task.STOPPED, Task.COMPLETE]:
            if self.gauge is None:
                self.gauge = wx.Gauge(self, wx.ID_ANY, 100, wx.Point(5, 3), wx.Size(60, self.GetSize().Get()[1] - 6))
            self.SetStatusText(task.name, 1)
            if task.status is Task.RUNNING:
                self.gauge.SetValue(task.percent)
            else:
                self.gauge.Pulse()
        else:
            self.SetStatusText("Idle", 1)
            if self.gauge is not None:
                self.gauge.Destroy()
                self.gauge = None
        self.timer.Start(100, True)
