import pytest
import wx


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
