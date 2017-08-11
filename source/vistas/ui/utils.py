import wx

from vistas.core.utils import get_platform
from vistas.ui.events import PluginOptionEvent, RedisplayEvent, NewLegendEvent, TimelineEvent, MessageEvent


def get_paint_dc(win):
    """ A utility function for obtaining a BufferedPaintDC on Windows. """
    if get_platform() == 'windows':
        dc = wx.BufferedPaintDC(win)
        dc.SetBrush(wx.Brush((win if win.UseBgCol() else win.GetParent()).GetBackgroundColour()))
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(0, 0, *win.GetSize().Get())
    else:
        dc = wx.PaintDC(win)
    return dc


def make_window_transparent(win):
    """ A utility function for creating transparent windows on Windows. """
    if get_platform() == 'windows':
        try:
            import ctypes
            handle = win.GetHandle()
            _winlib = ctypes.windll.user32
            old_flags = _winlib.GetWindowLongA(handle, -20)             # GWL_EXSTYLE
            old_flags |= 0x00080000                                     # old_flags | WS_EX_LAYERED
            _winlib.SetWindowLongA(handle, -20, old_flags)
            _winlib.SetLayeredWindowAttributes(handle, 262914, 255, 3)  # 262914 = RGB(2,3,4), 3 = LWA_ALPHA | LWA_COLORKEY
        except:
            print("Something went terribly, terribly wrong!")


def get_main_window() -> wx.Window:
    """ A utility function for return the application's main window. """
    return wx.GetTopLevelWindows()[0]   # Assumed to be MainWindow


def post_newoptions_available(plugin):
    """ A utility function for alerting the application that new plugin Options are available. """
    get_main_window().AddPendingEvent(PluginOptionEvent(plugin=plugin, change=PluginOptionEvent.NEW_OPTIONS_AVAILABLE))


def post_redisplay():
    """ A utility function for updating all 2D and 3D panels. """
    get_main_window().AddPendingEvent(RedisplayEvent())


def post_new_legend():
    """ A utility function for alerting the application that legends need to be refreshed. """
    get_main_window().AddPendingEvent(NewLegendEvent())


def post_timeline_change(time, change):
    """ A utility function for alerting the application that a timeline change has occurred. """
    get_main_window().AddPendingEvent(TimelineEvent(time=time, change=change))


def post_message(msg, level):
    """ A utility function for posting a message to the user. """
    get_main_window().AddPendingEvent(MessageEvent(msg=msg, level=level))
