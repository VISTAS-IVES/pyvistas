from vistas.core.plugins.management import *
from vistas.core.paths import get_icon

import wx
import wx.core


class PluginsWindow(wx.Frame):
    def __init__(self, parent, id):
        super().__init__(parent, id, "Plugins")
        self.SetSize(500, 400)
        self.SetIcon(get_icon("plugin.ico"))
        self.CenterOnParent()

        main_panel = wx.Panel(self)
        main_splitter = wx.SplitterWindow(main_panel, style=wx.SP_3DSASH | wx.SP_LIVE_UPDATE)
        self.plugins_list = wx.ListCtrl(main_splitter, wx.ID_ANY, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES)

        self.plugin_details_panel = wx.Panel(main_splitter)
        self.no_plugin_static = wx.StaticText(self.plugin_details_panel, wx.ID_ANY, "No plugin selected.")
        self.name_label_static = wx.StaticText(self.plugin_details_panel, wx.ID_ANY, "Name:")
        self.name_static = wx.StaticText(self.plugin_details_panel, wx.ID_ANY, "")
        self.type_label_static = wx.StaticText(self.plugin_details_panel, wx.ID_ANY, "Type:")
        self.type_static = wx.StaticText(self.plugin_details_panel, wx.ID_ANY, "")
        self.version_label_static = wx.StaticText(self.plugin_details_panel, wx.ID_ANY, "Version:")
        self.version_static = wx.StaticText(self.plugin_details_panel, wx.ID_ANY, "")
        self.author_label_static = wx.StaticText(self.plugin_details_panel, wx.ID_ANY, "Author:")
        self.author_static = wx.StaticText(self.plugin_details_panel, wx.ID_ANY, "")
        self.description_label_static = wx.StaticText(self.plugin_details_panel, wx.ID_ANY, "Description:")
        self.description_static = wx.StaticText(self.plugin_details_panel, wx.ID_ANY, "")

        self.plugins_list.SetAutoLayout(True)
        self.plugins_list.InsertColumn(0, "Name", wx.LIST_FORMAT_LEFT, 200)
        self.plugins_list.InsertColumn(1, "Type", wx.LIST_FORMAT_LEFT, 100)
        self.plugins_list.InsertColumn(2, "Version", wx.LIST_FORMAT_LEFT, 75)
        self.plugin_details_panel.SetBackgroundColour(wx.WHITE)
        main_splitter.SplitHorizontally(self.plugins_list, self.plugin_details_panel, 100)

        font = self.name_label_static.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        for label in ["name_label", "type_label", "version_label", "author_label", "description_label"]:
            getattr(self, label + "_static").SetFont(font)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)

        main_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        main_panel.SetSizer(main_panel_sizer)
        main_sizer.Add(main_panel, 1, wx.EXPAND)
        main_panel_sizer.Add(main_splitter, 1, wx.EXPAND)

        self.plugin_details_sizer = wx.BoxSizer(wx.VERTICAL)
        self.plugin_details_panel.SetSizer(self.plugin_details_sizer)
        self.plugin_details_sizer.Add(self.no_plugin_static, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 5)
        self.plugin_details_sizer.Add(self.name_label_static, 0, wx.TOP, 5)
        self.plugin_details_sizer.Add(self.name_static)
        self.plugin_details_sizer.Add(self.type_label_static, 0, wx.TOP, 5)
        self.plugin_details_sizer.Add(self.type_static)
        self.plugin_details_sizer.Add(self.version_label_static, 0, wx.TOP, 5)
        self.plugin_details_sizer.Add(self.version_static)
        self.plugin_details_sizer.Add(self.author_label_static, 0, wx.TOP, 5)
        self.plugin_details_sizer.Add(self.author_static)
        self.plugin_details_sizer.Add(self.description_label_static, 0, wx.TOP, 5)
        self.plugin_details_sizer.Add(self.description_static)

        self.HidePluginDetails()

        self.Bind(wx.EVT_CLOSE, self.OnWindowClose)
        self.plugins_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
        self.plugins_list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemDeselected)

        self.plugins = list(get_plugins())
        self.viz_plugins = get_visualization_plugins()
        self.data_plugins = get_data_plugins()
        self.plugins = self.viz_plugins + self.data_plugins
        self.plugins.sort(key=lambda x: x.id)

        for p in self.plugins:
            self.AddPlugin(p)

    def HidePluginDetails(self):
        self.no_plugin_static.Show()
        self.name_label_static.Hide()
        self.name_static.Hide()
        self.type_label_static.Hide()
        self.type_static.Hide()
        self.version_label_static.Hide()
        self.version_static.Hide()
        self.author_label_static.Hide()
        self.author_static.Hide()
        self.description_label_static.Hide()
        self.description_static.Hide()
        self.plugin_details_panel.Layout()

    def ShowPluginDetails(self):
        self.no_plugin_static.Hide()
        self.name_label_static.Show()
        self.name_static.Show()
        self.type_label_static.Show()
        self.type_static.Show()
        self.version_label_static.Show()
        self.version_static.Show()
        self.author_label_static.Show()
        self.author_static.Show()
        self.description_label_static.Show()
        self.description_static.Show()
        self.plugin_details_panel.Layout()

    def SetPluginDetails(self, plugin):
        self.name_static.SetLabel(plugin.name)
        if plugin in self.data_plugins:
            self.type_static.SetLabel("Data Plugin")
        elif plugin in self.viz_plugins:
            self.type_static.SetLabel("Visualization Plugin")
        else:
            self.type_static.SetLabel("Unknown plugin type")
        self.version_static.SetLabel(plugin.version)
        self.author_static.SetLabel(plugin.author)
        self.description_static.SetLabel(plugin.description)
        self.description_static.Wrap(self.plugin_details_panel.GetClientSize().x)

    def AddPlugin(self, plugin):
        i = self.plugins_list.GetItemCount()
        self.plugins_list.InsertItem(i, "")
        self.plugins_list.SetItem(i, 0, plugin.name)
        if plugin in self.data_plugins:
            label = "Data"
        elif plugin in self.viz_plugins:
            label = "Visualization"
        else:
            label = "Unknown"
        self.plugins_list.SetItem(i, 1, label)
        self.plugins_list.SetItem(i, 2, plugin.version)

    def OnWindowClose(self, event):
        self.Hide()

    def OnItemSelected(self, event):
        self.SetPluginDetails(self.plugins[event.GetIndex()])
        self.ShowPluginDetails()

    def OnItemDeselected(self, event):
        self.HidePluginDetails()
