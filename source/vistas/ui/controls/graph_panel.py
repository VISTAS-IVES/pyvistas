import wx

from vistas.core.plugins.visualization import EVT_VISUALIZATION_RENDERED, VisualizationPlugin2D, \
    EVT_VISUALIZATION_UPDATED
from vistas.ui.project import Project


class GraphPanel(wx.Panel):
    def __init__(self, parent, id):
        super().__init__(parent, id)

        self._visualization = None
        self.visualizations = []

        self.visualization_choice = wx.Choice(self, wx.ID_ANY)
        self.image_panel = wx.Panel(self, wx.ID_ANY)
        self.static_image = wx.StaticBitmap(self.image_panel, wx.ID_ANY)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        sizer.Add(self.visualization_choice, 0, wx.EXPAND)
        sizer.Add(self.image_panel, 1, wx.EXPAND)

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.image_panel.SetSizer(panel_sizer)
        panel_sizer.Add(self.static_image, 1, wx.EXPAND)

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(EVT_VISUALIZATION_RENDERED, self.OnVisualizationRendered)
        self.static_image.Bind(wx.EVT_RIGHT_DOWN, self.OnRightClick)
        self.visualization_choice.Bind(wx.EVT_CHOICE, self.OnChoice)
        parent.Bind(EVT_VISUALIZATION_UPDATED, self.OnVisualizationUpdated)

        self.Fit()

        self.static_image.SetBackgroundColour(wx.Colour(0, 0, 0))

    @property
    def visualization(self):
        return self._visualization

    @visualization.setter
    def visualization(self, visualization):
        self._visualization = visualization
        self.static_image.SetBitmap(wx.Bitmap())
        self.RefreshVisualization()

    def RefreshVisualization(self):
        if self.visualization is not None:
            size = self.image_panel.GetClientSize()
            self.visualization.visualize(size.x, size.y, handler=self)

    def OnVisualizationRendered(self, event):
        if event.image is None:
            self.static_image.SetBitmap(wx.Bitmap())
            return

        wximage = wx.Image(*event.image.size)
        wximage.SetData(event.image.convert('RGB').tobytes())
        self.static_image.SetBitmap(wximage.ConvertToBitmap())

    def PopulateVisualizations(self):
        self.visualizations = [
            x for x in Project.get().all_visualizations if
            isinstance(x.visualization, VisualizationPlugin2D)
        ]
        self.visualization_choice.Clear()

        for i, node in enumerate(self.visualizations):
            visualization = node.visualization
            self.visualization_choice.Append(node.label)
            if visualization == self.visualization:
                self.visualization_choice.SetSelection(i)

        if self.visualizations and self.visualization is None:
            self.visualization_choice.SetSelection(0)
            self.visualization = self.visualizations[0].visualization

    def OnChoice(self, event):
        self.visualization = self.visualizations[event.GetSelection()].visualization
        self.RefreshVisualization()

    def OnRightClick(self, event):
        if self.visualization is None:
            return

        menu = wx.Menu()
        menu.Append(1, 'Copy')
        menu.Bind(wx.EVT_MENU, self.OnGraphPopupMenu)
        self.PopupMenu(menu)

    def OnGraphPopupMenu(self, event):
        if event.GetId() == 1:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.BitmapDataObject(self.static_image.GetBitmap()))

    def OnSize(self, event):
        self.RefreshVisualization()
        event.Skip(True)

    def OnVisualizationUpdated(self, event):
        self.RefreshVisualization()
