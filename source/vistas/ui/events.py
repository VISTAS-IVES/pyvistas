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


RedisplayEvent, EVT_REDISPLAY = wx.lib.newevent.NewEvent()
