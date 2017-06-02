import asyncio
import logging
import sys
import traceback

import wx

import vistas
from vistas.ui.controllers.app import AppController
from vistas.ui.windows.exception_dialog import ExceptionDialog

logger = logging.getLogger(__name__)

HandleExceptionEvent, EVT_HANDLE_EXCEPTION = wx.lib.newevent.NewEvent()


class App(wx.App):
    _global_app = None
    init = False

    @classmethod
    def get(cls):
        if cls._global_app is None:
            cls._global_app = App()
        return cls._global_app

    def __init__(self):
        self.app_controller = None

        super().__init__()

        self.Bind(EVT_HANDLE_EXCEPTION, self.OnHandleException)

    def OnInit(self):
        logger.debug('VISTAS {} starting...'.format(vistas.__version__))

        sys.excepthook = exception_hook

        if sys.platform == 'win32':
            asyncio.set_event_loop(asyncio.ProactorEventLoop())
        else:
            asyncio.set_event_loop(asyncio.SelectorEventLoop())

        self.app_controller = AppController()

        logger.debug('VISTAS started')

        App.init = True

        return True

    def OnHandleException(self, event):
        dialog = ExceptionDialog(self.app_controller.main_window, event.message)
        dialog.ShowModal()
        dialog.Destroy()


def exception_hook(exc_type, value, trace):
    exception_message = ''.join(traceback.format_exception(exc_type, value, trace))
    logger.error('Unhandled exception\n{}'.format(exception_message))

    if App.init:
        wx.PostEvent(App.get(), HandleExceptionEvent(message=exception_message))
