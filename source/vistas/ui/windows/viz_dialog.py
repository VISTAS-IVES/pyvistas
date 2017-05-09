from vistas.core.plugins.visualization import VisualizationPlugin
from vistas.ui.controls.histogram_ctrl import HistogramCtrl
from vistas.ui.controls.options_panel import OptionsPanel

import wx
import wx.richtext


class VisualizationDialog(wx.Frame):

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

            # Todo: HISTOGRAM_CTRL_RANGE_VALUE_CHANGED_EVT -> OnFilterChange
            self.clear_filter_button.Bind(wx.EVT_BUTTON, self.OnClearFilter)

        self.options_panel.options = self.viz.get_options()
        self.options_panel.plugin = self.viz
        self.RefreshInfoText()
        self.RefreshDataOptions()
        self.Layout()

        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPage)
        # Todo: VI_EVENT_TIMEILNE_VALUE_CHANGED -> OnTimelineChanged
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def RefreshInfoText(self):
        pass

    def AddMultipleDataChoice(self, available_choices, selected, role_idx, input_indx, label):
        pass

    def RefreshDataOptions(self):
        pass

    def OnClose(self, event):
        main_window = wx.GetTopLevelParent(self.GetParent())
        main_window.SetOptions(self.viz.get_options(), self.viz)
        event.Skip()

    def OnChoice(self, event):
        pass

    def OnPage(self, event):
        pass

    def OnFilterChange(self, event):
        pass

    def OnClearFilter(self, event):
        pass

    def OnTimelineChange(self, event):
        pass
