import wx

from vistas.core.paths import get_resource_bitmap


class ProjectTreeCtrl(wx.TreeCtrl):
    def __init__(self, style=wx.TR_HAS_BUTTONS, *args, **kwargs):
        super().__init__(style=style, *args, **kwargs)

        images = wx.ImageList(20, 20, True, 5)
        images.Add(get_resource_bitmap('folder_icon.png'))
        images.Add(get_resource_bitmap('data_icon.png'))
        images.Add(get_resource_bitmap('viz_icon.png'))
        images.Add(get_resource_bitmap('scene_icon.png'))
        images.Add(get_resource_bitmap('flythrough.png'))

        self.AssignImageList(images)

    def AppendFolderItem(self, parent, label, data=None):
        item = self.AppendItem(parent, label, 0, -1, data)
        self.SetItemHasChildren(item, True)

        return item

    def AppendDataItem(self, parent, label, data=None):
        return self.AppendItem(parent, label, 1, -1, data)

    def AppendVisualizationItem(self, parent, label, data=None):
        return self.AppendItem(parent, label, 2, -1, data)

    def AppendSceneItem(self, parent, label, data=None):
        return self.AppendItem(parent, label, 3, -1, data)

    def AppendFlythroughItem(self, parent, label, data=None):
        return self.AppendItem(parent, label, 4, -1, data)


class ProjectPanel(wx.Panel):
    def __init__(self, parent, id):
        super().__init__(parent, id)

        self.notebook = wx.Notebook(self, wx.ID_ANY, style=wx.NB_TOP)

        tree_style = (
            wx.TR_EDIT_LABELS | wx.TR_NO_LINES | wx.TR_FULL_ROW_HIGHLIGHT | wx.TR_EXTENDED | wx.TR_HAS_BUTTONS |
            wx.TR_LINES_AT_ROOT
        )

        self.data_tree = ProjectTreeCtrl(self.notebook, wx.ID_ANY, style=tree_style)
        self.visualization_tree = ProjectTreeCtrl(self.notebook, wx.ID_ANY, style=tree_style)
        self.data_tree.Expand(self.data_tree.GetRootItem())
        self.visualization_tree.Expand(self.visualization_tree.GetRootItem())

        self.notebook.AddPage(self.data_tree, 'Data')
        self.notebook.AddPage(self.visualization_tree, 'Visualizations')

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        sizer.Add(self.notebook, 1, wx.EXPAND)

        self.data_tree.AddRoot('Project Data')
        self.visualization_tree.AddRoot('Project Visualizations')

