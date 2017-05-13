import asyncio, sys

import wx

from vistas.ui.controllers.app import AppController


class App(wx.App):

    _global_app = None

    @classmethod
    def get(cls):
        if cls._global_app is None:
            cls._global_app = App()
        return cls._global_app

    def __init__(self):
        super().__init__()

        self.app_controller = None

    def OnInit(self):
        if sys.platform == 'win32':
            asyncio.set_event_loop(asyncio.ProactorEventLoop())
        else:
            asyncio.set_event_loop(asyncio.SelectorEventLoop())

        self.app_controller = AppController()

        return True

    @property
    def main_window(self):
        return wx.GetTopLevelWindows()[0]
