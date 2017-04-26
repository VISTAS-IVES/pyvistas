from vistas.core.paths import get_icon, get_resource_bitmap
from vistas.ui.controls.gl_canvas import GLCanvas
from vistas.ui.controls.draggable_value import DraggableValue

import wx


class FlythroughDialog(wx.Frame):
    ADD_POINT = 101
    FLYTHROUGH_FORWARD = 102
    FLYTHROUGH_BACKWARD = 103
    FLYTHROUGH_PLAY = 104
    FLYTHROUGH_PAUSE = 105
    FLYTHROUGH_RESET = 106

    FLYTHROUGH_POPUP_AUTOKEYFRAME = 201

    VALUE_PER_PX = 0.01

    def __init__(self, parent, id, flythrough, project=None):
        super().__init__(parent, id, 'Flythrough Animation')

        self.flythrough = flythrough

        self.CenterOnParent()
        size = wx.Size(600,580)
        self.SetMinSize(size)
        self.SetSize(size)

        main_panel = wx.Panel(self, wx.ID_ANY)
        self.SetIcon(get_icon("flythrough.ico"))
        # Todo: add PNG handler?

        self.gl_canvas = GLCanvas(main_panel, wx.ID_ANY, flythrough.camera)  # Todo: attributes?

        keyframe_panel = wx.Panel(main_panel, wx.ID_ANY)
        keyframe_timeline = wx.Panel(keyframe_panel, wx.ID_ANY) # Todo: implement KeyframeTimeline, add args [0, flythrough.num_keyframes, 0, flythrough.fps]

        # camera controls
        draggable_panel = wx.Panel(main_panel, wx.ID_ANY)
        position_label = wx.StaticText(draggable_panel, wx.ID_ANY, "Position: ")
        self.position_x = DraggableValue(draggable_panel, wx.ID_ANY, 0, self.VALUE_PER_PX)
        self.position_y = DraggableValue(draggable_panel, wx.ID_ANY, 0, self.VALUE_PER_PX)
        self.position_z = DraggableValue(draggable_panel, wx.ID_ANY, 0, self.VALUE_PER_PX)

        direction_label = wx.StaticText(draggable_panel, wx.ID_ANY, "Direction: ")
        self.direction_x = DraggableValue(draggable_panel, wx.ID_ANY, 0, self.VALUE_PER_PX)
        self.direction_y = DraggableValue(draggable_panel, wx.ID_ANY, 0, self.VALUE_PER_PX)
        self.direction_z = DraggableValue(draggable_panel, wx.ID_ANY, 0, self.VALUE_PER_PX)

        up_label = wx.StaticText(draggable_panel, wx.ID_ANY, "Up: ")
        self.up_x = DraggableValue(draggable_panel, wx.ID_ANY, 0, self.VALUE_PER_PX)
        self.up_y = DraggableValue(draggable_panel, wx.ID_ANY, 0, self.VALUE_PER_PX)
        self.up_z = DraggableValue(draggable_panel, wx.ID_ANY, 0, self.VALUE_PER_PX)

        # playback
        playback_panel = wx.Panel(main_panel, wx.ID_ANY)
        record_button = wx.BitmapButton(playback_panel, self.FLYTHROUGH_ADD_POINT, get_resource_bitmap("camera_capture_2.png"))
        record_button.SetToolTip("Record Keyframe")
        backward_button = wx.BitmapButton(playback_panel, self.FLYTHROUGH_BACKWARD, get_resource_bitmap("camera_backward.png"))
        backward_button.SetToolTip("Back one frame")
        self.play_label = get_resource_bitmap("go_button.png")
        self.pause_label = get_resource_bitmap("pause_button.png")
        self.play_pause_button = wx.BitmapButton(playback_panel, self.FLYTHROUGH_PLAY, self.play_label)
        self.play_pause_button.SetToolTip("Play flythrough")
        forward_button = wx.BitmapButton(playback_panel, self.FLYTHROUGH_FORWARD, get_resource_bitmap("camera_forward.png"))
        forward_button.SetToolTip("Forward one frame")
        reset_button = wx.BitmapButton(playback_panel, self.FLYTHROUGH_RESET, get_resource_bitmap("reset_button.png"))
        reset_button.SetToolTip("Reset flythrough")
        
        # fps
        fps_label = wx.StaticText(playback_panel, wx.ID_ANY, "Frames Per Second:")
        self.fps_ctrl = wx.TextCtrl(playback_panel, wx.ID_ANY, self.flythrough.fps)
        self.fps_ctrl.SetWindowStyle(wx.TE_CENTRE)
        self.fps_ctrl.SetToolTip("Change Frames Per Second")
        
        # length
        length_label = wx.StaticText(playback_panel, wx.ID_ANY, "Length (sec):")
        self.length_ctrl = wx.TextCtrl(playback_panel, wx.ID_ANY, self.flythrough.length)
        self.length_ctrl.SetWindowStyle(wx.TE_CENTRE)
        self.length_ctrl.SetToolTip("Change length of flythrough animation")

        # layout
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_panel.SetSizer(main_sizer)

        keyframe_sizer = wx.BoxSizer(wx.VERTICAL)
        keyframe_panel.SetSizer(keyframe_sizer)
        keyframe_sizer.Add(keyframe_timeline, 0, wx.EXPAND | wx.RIGHT)

        draggable_sizer = wx.BoxSizer(wx.HORIZONTAL)
        draggable_sizer.Add(position_label)
        draggable_sizer.Add(self.position_x, 0, wx.RIGHT, 5)
        draggable_sizer.Add(self.position_y, 0, wx.RIGHT, 5)
        draggable_sizer.Add(self.position_z, 0, wx.RIGHT, 5)
        draggable_sizer.AddStretchSpacer(5)
        draggable_sizer.Add(direction_label)
        draggable_sizer.Add(self.direction_x, 0, wx.RIGHT, 5)
        draggable_sizer.Add(self.direction_y, 0, wx.RIGHT, 5)
        draggable_sizer.Add(self.direction_z, 0, wx.RIGHT, 5)
        draggable_sizer.AddStretchSpacer(5)
        draggable_sizer.Add(up_label)
        draggable_sizer.Add(self.up_x, 0, wx.RIGHT, 5)
        draggable_sizer.Add(self.up_y, 0, wx.RIGHT, 5)
        draggable_sizer.Add(self.up_z, 0, wx.RIGHT, 5)
        draggable_panel.SetSizer(draggable_sizer)

        playback_sizer = wx.BoxSizer(wx.HORIZONTAL)
        playback_sizer.Add(record_button, 0, wx.ALIGN_CENTRE_VERTICAL | wx.ALL, 5)
        playback_sizer.Add(backward_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        playback_sizer.Add(self.play_pause_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        playback_sizer.Add(reset_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        playback_sizer.Add(forward_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        playback_sizer.AddStretchSpacer()
        playback_sizer.Add(fps_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 1)
        playback_sizer.Add(self.fps_ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        playback_sizer.Add(length_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 1)
        playback_sizer.Add(self.length_ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        playback_panel.SetSizer(playback_sizer)

        main_sizer.Add(self.gl_canvas, 1, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(keyframe_panel, 0, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(draggable_panel, 0, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(playback_panel, 0, wx.ALL | wx.EXPAND, 5)

        self.timer = wx.Timer(self, wx.ID_ANY)

        self.Bind(wx.EVT_TIMER, self.OnTimer)
        self.Bind(wx.EVT_SIZE, self.OnSize)

        self.Bind(wx.EVT_BUTTON, self.RecordKeyframe, id=self.FLYTHROUGH_ADD_POINT)
        self.Bind(wx.EVT_BUTTON, self.OnPlayPause, id=self.FLYTHROUGH_PLAY)
        self.Bind(wx.EVT_BUTTON, self.OnReset, id=self.FLYTHROUGH_RESET)
        self.Bind(wx.EVT_BUTTON, self.OnBackward, id=self.FLYTHROUGH_BACKWARD)
        self.Bind(wx.EVT_BUTTON, self.OnForward, id=self.FLYTHROUGH_FORWARD)

        self.fps_ctrl.Bind(wx.EVT_TEXT_ENTER, self.OnFPSChange)
        self.fps_ctrl.Bind(wx.EVT_KILL_FOCUS, self.OnFPSChange)
        self.length_ctrl.Bind(wx.EVT_TEXT_ENTER, self.OnLengthChange)
        self.length_ctrl.Bind(wx.EVT_KILL_FOCUS, self.OnLengthChange)

        # Todo: RecalculateKeyframeIndices?
        self.flythrough.update_camera_to_keyframe(0)
        self.UpdateDraggablesFromCamera()
        # Todo: Reset camera interactor position?

    def UpdateDraggablesFromCamera(self):
        self.position_x.value, self.position_y.value, self.position_z.value, _ = self.flythrough.camera.get_position().v
        self.direction_x.value, self.direction_y.value, self.direction_z.value, _ = self.flythrough.camera.get_direction().v
        self.up_x.value, self.up_y.value, self.up_z.value, _ = self.flythrough.camera.get_up_vector().v

    def UpdateTimeline(self):
        pass

    def OnTimer(self, event):
        pass

    def OnSize(self, event):
        pass

    def RecordKeyframe(self, event):
        pass

    def OnPlayPause(self, event):
        pass

    def OnReset(self, event):
        pass

    def OnBackward(self, event):
        pass

    def OnForward(self, event):
        pass

    def OnFPSChange(self, event):
        pass

    def OnLengthChange(self, event):
        pass

    def OnRightClick(self, event):
        pass

    def OnCanvasWheel(self, event):
        pass

    def OnCanvasMotion(self, event):
        pass

