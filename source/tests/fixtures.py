import os
from typing import NamedTuple

import pytest
import sys
import wx

from vistas.ui.app import App


@pytest.fixture(scope='session')
def generic_app():
    class TestApp(wx.App):
        def OnInit(self):
            return True

    app = TestApp()
    yield app
    wx.CallAfter(app.ExitMainLoop)
    app.MainLoop()
    app.ProcessPendingEvents()


@pytest.fixture(scope='function')
def vistas_app():
    class TestResult:
        exc = None

    def run_test(callback):
        source_dir = os.path.dirname(os.path.dirname(__file__))
        os.chdir(source_dir)

        excepthook = sys.excepthook
        result = TestResult()

        app = App.get()

        def test_callback():
            sys.excepthook = excepthook

            try:
                callback()
            except Exception as e:
                result.exc = e
            finally:
                app.ExitMainLoop()

        timer = wx.Timer()
        timer.Bind(wx.EVT_TIMER, lambda event: test_callback())
        timer.Start(1, True)

        app.MainLoop()

        if result.exc is not None:
            raise result.exc

    return run_test
