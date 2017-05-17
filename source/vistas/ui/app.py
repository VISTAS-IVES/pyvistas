import asyncio
import sys

import logging
import traceback

import wx

from vistas.ui.controllers.app import AppController
from vistas.ui.windows.exception_dialog import ExceptionDialog

logger = logging.getLogger(__name__)


class App(wx.App):
    _global_app = None

    @classmethod
    def get(cls):
        if cls._global_app is None:
            cls._global_app = App()
        return cls._global_app

    def __init__(self):
        self.app_controller = None

        super().__init__()

    def OnInit(self):
        logger.debug('VISTAS starting...')

        sys.excepthook = exception_hook

        if sys.platform == 'win32':
            asyncio.set_event_loop(asyncio.ProactorEventLoop())
        else:
            asyncio.set_event_loop(asyncio.SelectorEventLoop())

        self.app_controller = AppController()

        logger.debug('VISTAS started')

        return True


def exception_hook(exc_type, value, trace):
    exception_message = ''.join(traceback.format_exception(exc_type, value, trace))
    logger.error('Unhandled exception\n{}'.format(exception_message))

    dialog = ExceptionDialog(App.get().app_controller.main_window, exception_message)
    dialog.ShowModal()
    dialog.Destroy()
