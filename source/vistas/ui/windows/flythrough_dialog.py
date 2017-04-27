from vistas.core.paths import get_icon, get_resource_bitmap
from vistas.core.graphics.vector import Vector
from vistas.ui.controls.gl_canvas import GLCanvas
from vistas.ui.controls.draggable_value import DraggableValue, EVT_DRAG_VALUE_EVENT
from vistas.ui.controls.keyframe_timeline import KeyframeTimeline

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

    def __init__(self, parent, id, flythrough):
        super().__init__(parent, id, 'Flythrough Animation')

        self.flythrough = flythrough
        self._auto_keyframe = True
        self.CenterOnParent()
        size = wx.Size(600,580)
        self.SetMinSize(size)
        self.SetSize(size)

        main_panel = wx.Panel(self, wx.ID_ANY)
        self.SetIcon(get_icon("flythrough.ico"))
        # Todo: add PNG handler?

        self.gl_canvas = GLCanvas(main_panel, wx.ID_ANY, flythrough.camera)  # Todo: attributes?

        keyframe_panel = wx.Panel(main_panel, wx.ID_ANY)

        self.keyframe_timeline = KeyframeTimeline(keyframe_panel, wx.ID_ANY, flythrough.num_keyframes, flythrough.fps)

        # camera controls
        draggable_panel = wx.Panel(main_panel, wx.ID_ANY)
        position_label = wx.StaticText(draggable_panel, wx.ID_ANY, "Position: ")
        direction_label = wx.StaticText(draggable_panel, wx.ID_ANY, "Direction: ")
        up_label = wx.StaticText(draggable_panel, wx.ID_ANY, "Up: ")

        # setup all draggable controls and init with 0 value
        self.position_x, self.position_y, self.position_z, self.direction_x, self.direction_y, self.direction_z, \
            self.up_x, self.up_y, self.up_z = [DraggableValue(draggable_panel, wx.ID_ANY, 0, self.VALUE_PER_PX)
                                               for _ in range(9)]

        # playback
        playback_panel = wx.Panel(main_panel, wx.ID_ANY)
        record_button = wx.BitmapButton(playback_panel, self.FLYTHROUGH_ADD_POINT,
                                        get_resource_bitmap("camera_capture_2.png"))
        record_button.SetToolTip("Record Keyframe")
        backward_button = wx.BitmapButton(playback_panel, self.FLYTHROUGH_BACKWARD,
                                          get_resource_bitmap("camera_backward.png"))
        backward_button.SetToolTip("Back one frame")
        self.play_label = get_resource_bitmap("go_button.png")
        self.pause_label = get_resource_bitmap("pause_button.png")
        self.play_pause_button = wx.BitmapButton(playback_panel, self.FLYTHROUGH_PLAY, self.play_label)
        self.play_pause_button.SetToolTip("Play flythrough")
        forward_button = wx.BitmapButton(playback_panel, self.FLYTHROUGH_FORWARD,
                                         get_resource_bitmap("camera_forward.png"))
        forward_button.SetToolTip("Forward one frame")
        reset_button = wx.BitmapButton(playback_panel, self.FLYTHROUGH_RESET,
                                       get_resource_bitmap("reset_button.png"))
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
        keyframe_sizer.Add(self.keyframe_timeline, 0, wx.EXPAND | wx.RIGHT)

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

        # Bind events
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

        # create popup menu once
        self.popup_menu = wx.Menu()
        self.popup_menu.AppendCheckItem(self.FLYTHROUGH_POPUP_AUTOKEYFRAME, "Auto Keyframe",
                                        "If enabled, moving the camera will set a keyframe.")
        self.popup_menu.Bind(wx.EVT_MENU, self.OnPopupMenu)

        # bind events to gl_canvas
        self.gl_canvas.Bind(wx.EVT_RIGHT_DOWN, self.OnRightClick)
        self.gl_canvas.Bind(wx.EVT_MOUSEWHEEL, self.OnCanvasWheel)
        self.gl_canvas.Bind(wx.EVT_MOTION, self.OnCanvasMotion)

        self.Bind(EVT_DRAG_VALUE_EVENT, self.OnDragValue)

        # Todo: RecalculateKeyframeIndices?
        self.flythrough.update_camera_to_keyframe(0)
        self.UpdateDraggablesFromCamera()
        # Todo: Reset camera interactor position?

    def __del__(self):
        self.timer.Stop()
        # Todo: other?

    def UpdateDraggablesFromCamera(self):
        self.position_x.value, self.position_y.value, self.position_z.value, _ = \
            self.flythrough.camera.get_position().v
        self.direction_x.value, self.direction_y.value, self.direction_z.value, _ = \
            self.flythrough.camera.get_direction().v
        self.up_x.value, self.up_y.value, self.up_z.value, _ = self.flythrough.camera.get_up_vector().v

    def UpdateTimeline(self):
        if self._auto_keyframe:
            frame = self.keyframe_timeline.current_frame
            self.RecalculateKeyframeIndices()
            self.flythrough.add_keyframe(frame)

    def OnDragValue(self, event):
        pos = Vector(self.position_x.value, self.position_y.value, self.position_z.value)
        self.flythrough.camera.set_position(pos)
        self.flythrough.camera.set_up_vector(Vector(
            self.up_x.value, self.up_y.value, self.up_z.value
        ))
        direction = Vector(self.direction_x.value, self.direction_y.value, self.direction_z.value)
        self.flythrough.camera.set_point_of_interest(pos + direction)

        # Todo: UIPostRedisplay?
        # Todo: reset camera interactor position?
        self.UpdateTimeline()

    def OnTimer(self, event):
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

    def RecalculateKeyframeIndices(self):
        old_max_frame = self.keyframe_timeline.max_frame
        new_max_frame = self.flythrough.num_keyframes
        old_current_frame = self.keyframe_timeline.current_frame
        new_current_frame = int((old_current_frame * new_max_frame) / old_max_frame)
        self.keyframe_timeline.Clear()
        self.keyframe_timeline.max_frame = new_max_frame
        self.keyframe_timeline.current_frame = new_current_frame
        self.keyframe_timeline.keyframes = self.flythrough.keyframes

    def OnFPSChange(self, event):
        fps = int(self.fps_ctrl.GetValue())
        if fps >= 0:
            self.flythrough.fps = fps
            self.keyframe_timeline.fps = fps
            self.RecalculateKeyframeIndices()

    def OnLengthChange(self, event):
        length = int(self.length_ctrl.GetValue())
        if length >= 0:
            self.flythrough.length = length
            self.keyframe_timeline.length = length
            self.RecalculateKeyframeIndices()

    def OnCanvasWheel(self, event):
        if not self.timer.IsRunning():
            self.UpdateDraggablesFromCamera()
            self.UpdateTimeline()
        event.Skip()

    def OnCanvasMotion(self, event):
        if event.LeftIsDown() and not self.timer.IsRunning():
            self.UpdateDraggablesFromCamera()
            self.UpdateTimeline()
        event.Skip()

    def OnRightClick(self, event):
        if event.RightIsDown():
            self.popup_menu.Check(self.FLYTHROUGH_POPUP_AUTOKEYFRAME, self._auto_keyframe)
            self.PopupMenu(self.popup_menu, self.gl_canvas.ScreenToClient(event.GetPosition()))

    def OnPopupMenu(self, event):
        event_id = event.GetId()
        if event_id == self.FLYTHROUGH_POPUP_AUTOKEYFRAME:
            self._auto_keyframe = not self._auto_keyframe

    def OnSize(self, event):
        self.gl_canvas.Refresh()
        self.keyframe_timeline.Refresh()
        event.Skip()
