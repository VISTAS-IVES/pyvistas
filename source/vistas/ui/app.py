import wx

from vistas.ui.controllers.app import AppController


class App(wx.App):
    def __init__(self):
        super().__init__()

        self.event_timer = None
        self.preferences = None
        self.app_controller = None

    def OnInit(self):
        self.event_timer = wx.Timer(self)
        self.app_controller = AppController()

        return True
