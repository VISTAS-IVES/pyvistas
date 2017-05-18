import wx.lib.newevent


ProjectChangedEventBase, EVT_COMMAND_PROJECT_CHANGED = wx.lib.newevent.NewEvent()


class ProjectChangedEvent(ProjectChangedEventBase):
    ADDED_VISUALIZATION = 'added_visualization'
    ADDED_FOLDER = 'added_folder'
    ADDED_DATA = 'added_data'
    ADDED_SCENE = 'added_scene'
    ADDED_FLYTHROUGH = 'added_flythrough'
    DELETED_ITEM = 'deleted_item'
    RENAMED_ITEM = 'renamed_item'
    PROJECT_RESET = 'project_reset'

    def __init__(self, node=None, change=None):
        super().__init__(node=node, change=change)


PluginOptionEventBase, EVT_PLUGIN_OPTION = wx.lib.newevent.NewEvent()


class PluginOptionEvent(PluginOptionEventBase):
    OPTION_CHANGED = 0
    NEW_OPTIONS_AVAILABLE = 1

    def __init__(self, plugin=None, option=None, change=None):
        super().__init__(plugin=plugin, option=option, change=change)


TimelineEventBase, EVT_TIMELINE_CHANGED = wx.lib.newevent.NewEvent()


class TimelineEvent(TimelineEventBase):
    VALUE_CHANGED = 0
    ATTR_CHANGED = 1

    def __init__(self, time=None, timeline=None, change=None):
        super().__init__(time=time, timeline=timeline, change=change)


MessageEventBase, EVT_MESSAGE = wx.lib.newevent.NewEvent()


class MessageEvent(MessageEventBase):
    NORMAL = 0
    ERROR = 1
    CRITICAL = 2

    def __init__(self, msg='', level=NORMAL):
        super().__init__(msg=msg, level=level)


# Event for alerting the UI to refresh canvases
RedisplayEvent, EVT_REDISPLAY = wx.lib.newevent.NewEvent()

# Event for alerting the UI to refresh legends
NewLegendEvent, EVT_NEW_LEGEND = wx.lib.newevent.NewEvent()
