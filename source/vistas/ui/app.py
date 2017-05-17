import asyncio
import sys

import wx

from vistas.ui.controllers.app import AppController


class App(wx.App):
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
