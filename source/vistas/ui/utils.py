import wx

from vistas.core.utils import get_platform
from vistas.ui.events import PluginOptionEvent, RedisplayEvent, NewLegendEvent, TimelineEvent, MessageEvent


def get_paint_dc(win):
    if get_platform() == 'windows':
        dc = wx.BufferedPaintDC(win)
        dc.SetBrush(wx.Brush((win if win.UseBgCol() else win.GetParent()).GetBackgroundColour()))
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(0, 0, *win.GetSize().Get())
    else:
        dc = wx.PaintDC(win)
    return dc


def make_window_transparent(win):
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
    return wx.GetTopLevelWindows()[0]   # Assumed to be MainWindow


def post_newoptions_available(plugin):
    get_main_window().AddPendingEvent(PluginOptionEvent(plugin=plugin, change=PluginOptionEvent.NEW_OPTIONS_AVAILABLE))


def post_redisplay():
    get_main_window().AddPendingEvent(RedisplayEvent())


def post_new_legend():
    get_main_window().AddPendingEvent(NewLegendEvent())


def post_timeline_change(time, change):
    get_main_window().AddPendingEvent(TimelineEvent(time=time, change=change))


def post_message(msg, level):
    get_main_window().AddPendingEvent(MessageEvent(msg=msg, level=level))
