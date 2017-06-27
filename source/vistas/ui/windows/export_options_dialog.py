from vistas.core.utils import get_platform
from vistas.core.timeline import Timeline

import wx
import wx.lib.intctrl


class ExportOptionsDialog(wx.Dialog):

    WMV = 0
    IMAGE = 1
    # Todo - add MPEG export option

    def __init__(self, parent, id, enable_frames_input=True):
        super().__init__(parent, id, "Export Options", style=wx.CAPTION | wx.STAY_ON_TOP)
        main_panel = wx.Panel(self, wx.ID_ANY)

        encoder_static = wx.StaticText(main_panel, wx.ID_ANY, "Export As:")
        self.encoder_choice = wx.Choice(main_panel, wx.ID_ANY, size=wx.Size(220, -1))

        if get_platform() == 'windows':
            self.encoder_choice.Append("WMV Video File")
        self.encoder_choice.Append("Individual Image Files")
        self.encoder_choice.SetSelection(0)

        initial_export_length = 30.0

        export_length_static = wx.StaticText(main_panel, wx.ID_ANY, "Length of export (in seconds):")
        self.export_length_ctrl = wx.lib.intctrl.IntCtrl(main_panel, wx.ID_ANY, value=initial_export_length, min=1,
                                                         size=wx.Size(50, -1))

        initial_export_timestamps = Timeline.app().num_timestamps / initial_export_length

        export_frames_static = wx.StaticText(main_panel, wx.ID_ANY, "Timestamps per second:")
        self.export_frames_ctrl = wx.lib.intctrl.IntCtrl(main_panel, wx.ID_ANY, value=initial_export_timestamps,
                                                         size=wx.Size(50, -1))

        self.export_frames_ctrl.Enable(enable_frames_input)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)

        main_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        main_panel.SetSizer(main_panel_sizer)

        main_panel_sizer.Add(encoder_static)
        main_panel_sizer.Add(self.encoder_choice, 0, wx.EXPAND)

        export_length_sizer = wx.BoxSizer(wx.HORIZONTAL)
        export_length_sizer.Add(export_length_static, 0, wx.RIGHT, 5)
        export_length_sizer.AddStretchSpacer(2)
        export_length_sizer.Add(self.export_length_ctrl, 0, wx.RIGHT, 5)
        main_panel_sizer.Add(export_length_sizer, 0, wx.ALL | wx.EXPAND, 10)

        export_frames_sizer = wx.BoxSizer(wx.HORIZONTAL)
        export_frames_sizer.Add(export_frames_static, 0, wx.RIGHT, 5)
        export_frames_sizer.AddStretchSpacer(2)
        export_frames_sizer.Add(self.export_frames_ctrl, 0, wx.RIGHT, 5)
        main_panel_sizer.Add(export_frames_sizer, 0, wx.ALL | wx.EXPAND, 10)

        main_sizer.Add(main_panel, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 5)

        self.export_length_ctrl.Bind(wx.EVT_KILL_FOCUS, self.OnExportLengthEndInput)
        self.export_length_ctrl.Bind(wx.EVT_COMMAND_ENTER, self.OnExportLengthEndInput)
        self.export_frames_ctrl.Bind(wx.EVT_KILL_FOCUS, self.OnExportFramesEndInput)
        self.export_frames_ctrl.Bind(wx.EVT_COMMAND_ENTER, self.OnExportFramesEndInput)

        self.Fit()

    def EncoderSelection(self):
        choice = self.encoder_choice.GetSelection()
        if choice == self.WMV:
            return self.WMV
        elif choice == self.IMAGE:
            return self.IMAGE
        return None

    @property
    def export_length(self):
        return self.export_length_ctrl.GetValue()

    def OnExportLengthEndInput(self, event):
        if self.export_frames_ctrl.Enabled():
            export_timestamps = Timeline.app().num_timestamps / self.export_length_ctrl.GetValue()
            self.export_frames_ctrl.SetValue(export_timestamps)

    def OnExportFramesEndInput(self, event):
        input_frames = self.export_frames_ctrl.GetValue()
        max_frames = Timeline.app().num_timestamps

        if input_frames > max_frames:
            input_frames = max_frames
        elif input_frames <= 0.0:
            input_frames = 1.0
        self.export_frames_ctrl.SetValue(input_frames)

        new_length = round(max_frames / input_frames)
        self.export_length_ctrl.SetValue(new_length)
