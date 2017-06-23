from vistas.core.utils import get_platform
from vistas.ui.events import PluginOptionEvent, RedisplayEvent, NewLegendEvent, TimelineEvent, MessageEvent
import wx


def get_paint_dc(win):
    if get_platform() == 'windows':
        dc = wx.BufferedPaintDC(win)
        dc.SetBrush(wx.Brush((win if win.UseBgCol() else win.GetParent()).GetBackgroundColour()))
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(0, 0, *win.GetSize().Get())
    else:
        dc = wx.PaintDC(win)
    return dc


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
