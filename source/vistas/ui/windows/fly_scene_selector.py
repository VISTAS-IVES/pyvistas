from vistas.ui.project import SceneNode

import wx


class FlythroughSceneSelector(wx.Dialog):

    def __init__(self, scene_list: [SceneNode], parent, id):
        super().__init__(parent, id, "Select Flythrough Scene", style=wx.CAPTION | wx.STAY_ON_TOP)
        self.CenterOnParent()
        main_panel = wx.Panel(self)
        text = wx.StaticText(main_panel, wx.ID_ANY, "Select a scene to create a flythrough for:")
        self.choice = wx.Choice(main_panel, wx.ID_ANY, size=wx.Size(200, -1))
        for scene in scene_list:
            self.choice.Append(scene.label)
        self.choice.SetSelection(0)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)
        main_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        main_panel.SetSizer(main_panel_sizer)
        main_panel_sizer.Add(text)
        main_panel_sizer.Add(self.choice, 0, wx.EXPAND)
        main_sizer.Add(main_panel, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND, wx.ALL, 5)
        self.Fit()

    def GetSceneChoice(self):
        return self.choice.GetSelection()
