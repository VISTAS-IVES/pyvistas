from collections import OrderedDict

import wx
import wx.richtext

from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.visualization import VisualizationPlugin, VisualizationPlugin2D, VisualizationPlugin3D
from vistas.ui.controls.histogram_ctrl import HistogramCtrl, HISTOGRAM_CTRL_RANGE_VALUE_CHANGED_EVT
from vistas.ui.controls.options_panel import OptionsPanel
from vistas.ui.events import ProjectChangedEvent
from vistas.ui.project import DataNode


class VisualizationDialog(wx.Frame):
    """ A window for viewing information about a VisualizationPlugin. """

    active_dialogs = []

    def __init__(self, parent, id, viz: VisualizationPlugin, project, node):
        super().__init__(
            parent, id, "Visualization Options",
            style=wx.CLOSE_BOX | wx.FRAME_FLOAT_ON_PARENT | wx.FRAME_TOOL_WINDOW | wx.CAPTION | wx.SYSTEM_MENU
        )
        self.SetSize(600, 400)
        self.CenterOnParent()

        self.viz = viz
        self.project = project
        self.node = node
        self.role_indexes = {}

        self.notebook = wx.Notebook(self, style=wx.NB_TOP)
        self.data_panel = wx.Panel(self.notebook)
        self.info_panel = wx.Panel(self.notebook)
        self.info_text = wx.richtext.RichTextCtrl(self.info_panel, wx.ID_ANY,
                                                  style=wx.richtext.RE_MULTILINE | wx.richtext.RE_READONLY)
        self.options_panel = OptionsPanel(self.notebook, wx.ID_ANY)

        self.notebook.AddPage(self.data_panel, "Data")
        self.notebook.AddPage(self.info_panel, "Info")
        self.notebook.AddPage(self.options_panel, "Options")

        if self.viz.is_filterable:
            self.filter_panel = wx.Panel(self.notebook)
            self.filter_histogram = HistogramCtrl(self.filter_panel, wx.ID_ANY)
            self.clear_filter_button = wx.Button(self.filter_panel, wx.ID_ANY, "Clear Filter")
            self.notebook.AddPage(self.filter_panel, "Filter")

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)
        main_sizer.Add(self.notebook, 1, wx.EXPAND)

        self.data_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.data_panel.SetSizer(self.data_panel_sizer)

        self.info_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.info_panel.SetSizer(self.info_panel_sizer)
        self.info_panel_sizer.Add(self.info_text, 1, wx.EXPAND)

        if self.viz.is_filterable:
            self.filter_panel_sizer = wx.BoxSizer(wx.VERTICAL)
            self.filter_panel.SetSizer(self.filter_panel_sizer)
            self.filter_panel_sizer.Add(self.filter_histogram, 1, wx.EXPAND)
            self.filter_panel_sizer.Add(self.clear_filter_button, 0, wx.TOP, 5)

            self.filter_histogram.Bind(HISTOGRAM_CTRL_RANGE_VALUE_CHANGED_EVT, self.OnFilterChange)
            self.clear_filter_button.Bind(wx.EVT_BUTTON, self.OnClearFilter)

        self.options_panel.options = self.viz.get_options()
        self.options_panel.plugin = self.viz
        self.RefreshInfoText()
        self.RefreshDataOptions()
        self.Layout()

        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPage)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.active_dialogs.append(self)

    def RefreshInfoText(self):

        info = OrderedDict()
        info['Plugin Name'] = self.viz.name
        info['Visualization Name'] = self.viz.visualization_name
        if isinstance(self.viz, VisualizationPlugin2D):
            viz_type = '2D Visualization'
        else:
            viz_type = '3D Visualization'
        info['Visualization Type'] = viz_type

        for i, role in enumerate(self.viz.data_roles):
            if role[0] is DataPlugin.RASTER:
                dtype = 'Grid Data'
            elif role[0] is DataPlugin.ARRAY:
                dtype = 'Array Data'
            elif role[0] is DataPlugin.FEATURE:
                dtype = 'Feature Data'
            else:
                dtype = 'Unknown data type'
            info['{} input'.format(role[1])] = dtype

        self.info_text.Clear()

        for entry in info.items():
            length = len(self.info_text.GetValue())
            self.info_text.AppendText("{}: ".format(entry[0]))
            self.info_text.SetSelection(length, length + len(entry[0]) + 1)
            self.info_text.ApplyBoldToSelection()
            self.info_text.AppendText("{}\n".format(entry[1]))

    def AddMultipleDataChoice(self, available_choices: [DataNode], selected, role_idx, input_idx, label):
        label_text = wx.StaticText(self.data_panel, wx.ID_ANY, label)
        data_choice = wx.Choice(self.data_panel, input_idx)
        self.role_indexes[data_choice] = role_idx

        index = data_choice.Append("None")
        data_choice.SetClientData(index, None)

        if selected is not None:
            index = data_choice.Append(selected.label)
            data_choice.SetClientData(index, selected.data)
            data_choice.Select(index)

        for potential_data in available_choices:
            index = data_choice.Append(potential_data.label)
            data_choice.SetClientData(index, potential_data.data)

        data_choice.Bind(wx.EVT_CHOICE, self.OnChoice)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(label_text, 0, wx.ALIGN_LEFT | wx.RIGHT, 20)
        sizer.Add(data_choice, 1, wx.ALIGN_RIGHT)
        self.data_panel_sizer.Add(sizer, 0, wx.EXPAND | wx.TOP, 1)

    def RefreshDataOptions(self):
        self.data_panel_sizer.Clear(True)
        for i, role in enumerate(self.viz.data_roles):
            roletype = role[0]
            label = "{} ({})".format(role[1], roletype.title())
            all_data_nodes = self.project.data_root.data_nodes
            current_data = []
            available_data = []

            if self.viz.role_supports_multiple_inputs(i):       # Multiple roles input
                current_inputs = self.viz.get_multiple_data(i)

                for node in all_data_nodes:
                    if roletype == node.data.data_type:
                        if node.data in current_inputs:
                            current_data.append(node)
                        else:
                            available_data.append(node)

                multiple_inputs_sizer = wx.BoxSizer(wx.HORIZONTAL)
                multiple_inputs_text = wx.StaticText(self.data_panel, wx.ID_ANY, "Multiple Inputs")
                multiple_inputs_sizer.Add(multiple_inputs_text, 0, wx.ALIGN_LEFT | wx.RIGHT, 20)
                self.data_panel_sizer.Add(multiple_inputs_sizer, 0, wx.EXPAND | wx.TOP, 10)

                last_idx = 0
                for node in current_data:
                    self.AddMultipleDataChoice(available_data, node, i, last_idx, label)
                    last_idx += 1

                self.AddMultipleDataChoice(available_data, None, i, last_idx, label)

            else:   # Single role input
                label_text = wx.StaticText(self.data_panel, wx.ID_ANY, label)
                data_choice = wx.Choice(self.data_panel, wx.ID_ANY)
                self.role_indexes[data_choice] = i
                index = data_choice.Append("None")
                data_choice.SetClientData(index, None)
                data_choice.Select(index)

                for node in all_data_nodes:
                    if roletype == node.data.data_type:
                        index = data_choice.Append(node.label)
                        data_choice.SetClientData(index, node.data)

                        if node.data == self.viz.get_data(i):
                            data_choice.Select(index)

                data_choice.Bind(wx.EVT_CHOICE, self.OnChoice)
                sizer = wx.BoxSizer(wx.HORIZONTAL)
                sizer.Add(label_text, 0, wx.ALIGN_LEFT | wx.RIGHT, 20)
                sizer.Add(data_choice, 1, wx.ALIGN_RIGHT)
                self.data_panel_sizer.Add(sizer, 0, wx.EXPAND | wx.TOP, 10)

        self.data_panel.Layout()

    def OnClose(self, event):
        main_window = wx.GetTopLevelParent(self.GetParent())
        main_window.SetOptions(self.viz.get_options(), self.viz)
        self.active_dialogs.remove(self)
        event.Skip()

    def OnChoice(self, event: wx.CommandEvent):
        data_choice = event.GetEventObject()
        data = data_choice.GetClientData(event.GetSelection())
        role_idx = self.role_indexes[data_choice]
        sub_idx = data_choice.GetId()

        has_multiple_inputs = self.viz.role_supports_multiple_inputs(role_idx)

        if data is not None:
            if has_multiple_inputs and sub_idx < self.viz.role_size(role_idx):
                self.viz.get_multiple_data(role_idx).pop(sub_idx)

            self.viz.set_data(data, role_idx)
        else:
            if has_multiple_inputs:
                if sub_idx < self.viz.role_size(role_idx):
                    self.viz.remove_subdata(role_idx, sub_idx)
            else:
                self.viz.set_data(None, role_idx)

        if isinstance(self.viz, VisualizationPlugin3D):
            bbox = self.viz.scene.bounding_box
            self.viz.refresh()

            if self.viz.scene.bounding_box != bbox:
                wx.PostEvent(
                    self.GetParent(),
                    ProjectChangedEvent(node=self.node, change=ProjectChangedEvent.ADDED_VISUALIZATION)
                )
            else:
                wx.PostEvent(
                    self.GetParent(),
                    ProjectChangedEvent(node=self.node, change=ProjectChangedEvent.VISUALIZATION_SET_DATA)
                )

        self.RefreshDataOptions()

    def OnPage(self, event):
        page = event.GetSelection()
        if page == 2:
            self.options_panel.options = self.viz.get_options()
            self.options_panel.plugin = self.viz
            self.options_panel.Layout()
        elif page == 3:
            self.filter_histogram.SetHistogram(self.viz.filter_histogram)
            if self.viz.is_filtered:
                self.filter_histogram.SetStops(self.viz.filter_min, self.viz.filter_max)
        event.Skip()

    def OnFilterChange(self, event):
        if self.viz.is_filterable:
            self.viz.set_filter(event.min_stop, event.max_stop)

    def OnClearFilter(self, event):
        if self.viz.is_filterable:
            self.filter_histogram.SetHistogram(self.viz.filter_histogram, True)
            self.viz.clear_filter()

    def TimelineChanged(self):
        if self.viz.is_filterable:
            self.filter_histogram.SetHistogram(self.viz.filter_histogram, not self.viz.is_filtered)
