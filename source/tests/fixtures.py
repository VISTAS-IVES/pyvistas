import pytest
import wx


@pytest.fixture(scope='function')
def generic_app():
    class TestApp(wx.App):
        exc = None

        def OnInit(self):
            frame = wx.Frame(None, wx.ID_ANY, 'Test')
            return True

    def run_test(callback):
        app = TestApp()

        def test_callback():
            try:
                callback()
            except Exception as e:
                app.exc = e
            finally:
                app.ExitMainLoop()

        timer = wx.Timer()
        timer.Bind(wx.EVT_TIMER, lambda event: test_callback())
        timer.Start(1, True)

        app.MainLoop()

        if app.exc is not None:
            raise app.exc

    return run_test
