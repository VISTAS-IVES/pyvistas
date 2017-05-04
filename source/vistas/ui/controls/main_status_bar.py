import wx


class MainStatusBar(wx.StatusBar):
    def __init__(self, parent, id):
        super().__init__(parent, id)
        self.SetFieldsCount(2, [70, -1])
        self.SetStatusText("Idle", 1)
        self.gauge = wx.Gauge(self, wx.ID_ANY, 100, wx.Point(5, 3), wx.Size(60, self.GetSize().Get()[1] - 6))
        # Todo: Start?

    def Notify(self):
        # Todo: Get newest task?
        task = None
        status = "Idle"

        # Todo: activate guage or turn off

        # Todo: Start?
