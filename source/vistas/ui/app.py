import wx

from vistas.ui.controllers.app import AppController


class App(wx.App):
    def __init__(self):
        super().__init__()

        self.app_controller = None

    def OnInit(self):
        self.app_controller = AppController()

        return True
