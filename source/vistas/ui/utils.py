from vistas.ui.events import PluginOptionEvent, RedisplayEvent, NewLegendEvent
import wx


def get_main_window() -> wx.Window:
    return wx.GetTopLevelWindows()[0]   # Assumed to be MainWindow


def post_newoptions_available():
    get_main_window().AddPendingEvent(PluginOptionEvent(change=PluginOptionEvent.NEW_OPTIONS_AVAILABLE))


def post_redisplay():
    get_main_window().AddPendingEvent(RedisplayEvent())


def post_new_legend():
    get_main_window().AddPendingEvent(NewLegendEvent())
