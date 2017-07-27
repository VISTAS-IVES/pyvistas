import asyncio
import logging
import os
import sys
import traceback
from logging.config import dictConfig

import wx

from vistas.core.encoders.video import DownloadFFMpegThread
from vistas.core.utils import get_platform
from vistas.ui.controllers.app import AppController
from vistas.ui.windows.exception_dialog import ExceptionDialog

try:
    import BUILD_CONSTANTS
except ImportError:
    BUILD_CONSTANTS = None

profile = getattr(BUILD_CONSTANTS, 'VISTAS_PROFILE', 'dev')
logger = logging.getLogger(__name__)

HandleExceptionEvent, EVT_HANDLE_EXCEPTION = wx.lib.newevent.NewEvent()


class App(wx.App):
    """ The top-level UI application. """
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
        if get_platform() == 'macos':
            logs_dir = os.path.join(wx.StandardPaths.Get().UserLocalDataDir, 'VISTAS', 'logs')
        else:
            logs_dir = os.path.join(wx.StandardPaths.Get().UserConfigDir, 'VISTAS', 'logs')

        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)

        dictConfig({
            'version': 1,
            'formatters': {
                'verbose': {
                    'format': '[%(levelname)s] [%(asctime)s:%(msecs).0f] %(message)s\n',
                    'datefmt': '%Y/%m/%d %H:%M:%S'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'verbose',
                    'level': 'DEBUG',
                    'stream': 'ext://sys.stdout'
                },
                'file': {
                    'class': 'logging.handlers.TimedRotatingFileHandler',
                    'formatter': 'verbose',
                    'level': 'DEBUG',
                    'filename': os.path.join(logs_dir, 'debug.txt'),
                    'when': 'D',
                    'interval': 7
                }
            },
            'loggers': {
                'vistas': {
                    'level': 'DEBUG',
                    'handlers': ['console'] if profile == 'dev' else ['file']
                }
            }
        })

        sys.excepthook = exception_hook

        if sys.platform == 'win32':
            asyncio.set_event_loop(asyncio.ProactorEventLoop())
        else:
            asyncio.set_event_loop(asyncio.SelectorEventLoop())

        self.app_controller = AppController()

        # Download FFmpeg
        DownloadFFMpegThread().start()

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
