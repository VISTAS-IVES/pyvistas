import os
import pytest
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


@pytest.fixture(scope='session')
def vistas_app():
    source_dir = os.path.dirname(os.path.dirname(__file__))
    os.chdir(source_dir)

    app = App.get()
    yield app
    wx.CallAfter(app.ExitMainLoop)
    app.MainLoop()
    app.ProcessPendingEvents()
