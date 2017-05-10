from collections import OrderedDict
from vistas.core.plugins.data import DataPlugin
from vistas.ui.controls.options_panel import OptionsPanel

import wx
import wx.richtext


class DataDialog(wx.Dialog):

    def __init__(self, parent, id, data: DataPlugin=None):
        super().__init__(parent, id, "Data Options")
        self.SetSize(600, 400)
        self.CenterOnParent()

        self.notebook = wx.Notebook(self, wx.ID_ANY, style=wx.NB_TOP)
        self.info_panel = wx.Panel(self.notebook)
        self.info_text = wx.richtext.RichTextCtrl(self.info_panel, wx.ID_ANY,
                                                  style=wx.richtext.RE_MULTILINE | wx.richtext.RE_READONLY)
        self.attr_panel = wx.Panel(self.notebook)
        self.attr_choice = wx.Choice(self.attr_panel)
        self.attr_text = wx.richtext.RichTextCtrl(self.attr_panel, wx.ID_ANY,
                                                  style=wx.richtext.RE_MULTILINE | wx.richtext.RE_READONLY)

        self.options_panel = OptionsPanel(self.notebook, wx.ID_ANY)

        self.notebook.AddPage(self.info_panel, "Info")
        self.notebook.AddPage(self.attr_panel, "Attributes")
        self.notebook.AddPage(self.options_panel, "Options")

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)
        main_sizer.Add(self.notebook, 1, wx.EXPAND)

        info_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.info_panel.SetSizer(info_panel_sizer)
        info_panel_sizer.Add(self.info_text, 1, wx.EXPAND)

        attr_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.attr_panel.SetSizer(attr_panel_sizer)
        attr_panel_sizer.Add(self.attr_choice, 0, wx.EXPAND | wx.BOTTOM, 10)
        attr_panel_sizer.Add(self.attr_text, 1, wx.EXPAND | wx.BOTTOM, 10)

        self.Layout()

        self.attr_choice.Bind(wx.EVT_CHOICE, self.OnAttrChoice)

        self._data = data
        self.info_text.Clear()

        if data is not None:
            info = OrderedDict()
            info['Plugin Name'] = data.name
            info['Data Name'] = data.data_name
            info['Data Source'] = data.path
            if data.data_type is DataPlugin.RASTER:
                info['Data Type'] = 'Grid'
                info['Cell Size'] = data.resolution
            if data.extent is not None:
                pass    # Todo: spatial units?
            if data.time_info is not None:
                pass    # Todo: temporal data units?
            self.SetInfo(self.info_text, info)
            self.attr_choice.Clear()
            for varname in data.variables:
                self.attr_choice.Append(varname)

    def OnAttrChoice(self, event):
        for i, varname in enumerate(self._data.variables):
            if i == event.GetSelection():
                info = OrderedDict()
                stats = self._data.variable_stats(varname)
                self.attr_text.Clear()
                if stats is not None:
                    info['Minimum Value'] = stats.min_value
                    info['Maximum Value'] = stats.max_value
                    info['No Data Value'] = stats.nodata_value
                    for row in stats.misc.items():
                        info[row[0]] = row[1]
                self.SetInfo(self.attr_text, info)
                break

    @staticmethod
    def SetInfo(text_ctrl: wx.richtext.RichTextCtrl, info):
        for row in info.items():
            length = len(text_ctrl.GetValue())
            text_ctrl.AppendText("{}: ".format(row[0]))
            text_ctrl.SetSelection(length, length+len(row[0])+1)
            text_ctrl.ApplyBoldToSelection()
            text_ctrl.AppendText("{}\n".format(row[1]))
