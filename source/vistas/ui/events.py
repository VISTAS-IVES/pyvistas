import wx.lib.newevent


# Event for alerting the UI that the project has changed in some way
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

# Event for alerting the UI that a plugin option has been updated
PluginOptionEventBase, EVT_PLUGIN_OPTION = wx.lib.newevent.NewEvent()


class PluginOptionEvent(PluginOptionEventBase):
    OPTION_CHANGED = 0
    NEW_OPTIONS_AVAILABLE = 1

    def __init__(self, plugin=None, option=None, change=None):
        super().__init__(plugin=plugin, option=option, change=change)

# Event for alerting the UI to make changes due to updates to a timeline
TimelineEventBase, EVT_TIMELINE_CHANGED = wx.lib.newevent.NewEvent()


class TimelineEvent(TimelineEventBase):
    VALUE_CHANGED = 0
    ATTR_CHANGED = 1

    def __init__(self, time=None, timeline=None, change=None):
        super().__init__(time=time, timeline=timeline, change=change)

# Event for alerting the UI to post a message to the user
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

# Event for alerting the UI gl_canvas instances that synced camera mode has changed
CameraChangedEvent, EVT_CAMERA_MODE_CHANGED = wx.lib.newevent.NewEvent()

# Event for sending a camera interactor event to other camera interactors
CameraSyncEventBase, EVT_CAMERA_SYNC = wx.lib.newevent.NewEvent()


class CameraSyncEvent(CameraSyncEventBase):

    def __init__(self, interactor=None):
        super().__init__(interactor=interactor)


# Event for informing a gl_canvas that the camera is starting a drag selection
CameraDragSelectStartEventBase, EVT_CAMERA_DRAG_SELECT_START = wx.lib.newevent.NewEvent()


class CameraDragSelectStartEvent(CameraDragSelectStartEventBase):
    def __init__(self, mode=None):
        super().__init__(mode=mode)


# Event for informing a gl_canvas that the camera has finished a drag selection
CameraDragSelectFinishEventBase, EVT_CAMERA_DRAG_SELECT_FINISH = wx.lib.newevent.NewEvent()


class CameraDragSelectFinishEvent(CameraDragSelectFinishEventBase):
    def __init__(self, mode=None, left=None, bottom=None, right=None, top=None, points=None):
        if any((left, bottom, right, top)) and points:
            raise TypeError("CameraDragSelectFinishEvent specified a box and a list of points")
        super().__init__(mode=mode, left=left, bottom=bottom, right=right, top=top, point=points)
