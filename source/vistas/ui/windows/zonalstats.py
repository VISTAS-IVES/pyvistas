import wx
import wx.grid
import wx.lib.scrolledpanel as scrolled


class ZonalStatisticsWindow(wx.Frame):
    """ A window for displaying data collected from a zonal statistics operation. """

    def __init__(self, parent, id):
        super().__init__(parent, id, "Zonal Statistics", style=wx.FRAME_TOOL_WINDOW | wx.SYSTEM_MENU | wx.CAPTION |
                                                               wx.CLOSE_BOX | wx.FRAME_FLOAT_ON_PARENT |
                                                               wx.RESIZE_BORDER)

        scroll_sizer = wx.BoxSizer(wx.VERTICAL)
        scroll_panel = scrolled.ScrolledPanel(self)
        self.grid = wx.grid.Grid(scroll_panel)
        scroll_sizer.Add(self.grid, 1, wx.EXPAND)
        scroll_panel.SetSizer(scroll_sizer)
        scroll_panel.SetupScrolling()

        self.grid.CreateGrid(1, 2)
        self.grid.SetRowLabelSize(0)
        self.grid.SetColLabelSize(0)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self._data = []

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value
        if isinstance(self._data, dict):
            self._data = [self._data]

        num_rows = self.grid.GetNumberRows()
        num_cols = self.grid.GetNumberCols()
        if num_rows:
            self.grid.DeleteRows(0, num_rows)
            self.grid.DeleteCols(0, num_cols)

        if self._data is None:
            return

        # Ensure name is first
        labels = list(self._data[0].keys() if isinstance(self._data[0], dict) else self._data[0][0].keys())
        if 'Data Name' in labels:
            label = labels.pop(labels.index('Data Name'))
            labels.insert(0, label)

        self.grid.AppendRows(1)
        for i, label in enumerate(labels):
            self.grid.AppendCols(1)
            self.grid.SetCellValue(0, i, label)

        num_rows = 0
        for data in self._data:
            if isinstance(data, dict):
                self.grid.AppendRows(1)
                num_rows += 1
                for key in data.keys():
                    col = labels.index(key)
                    self.grid.SetCellValue(num_rows, col, str(data[key]))
            elif isinstance(data, list):
                for inner_row in data:
                    if isinstance(inner_row, dict):
                        self.grid.AppendRows(1)
                        num_rows += 1
                        for key in inner_row.keys():
                            col = labels.index(key)
                            self.grid.SetCellValue(num_rows, col, str(inner_row[key]))

        self.grid.AutoSizeRows(setAsMin=True)
        if not self.IsShown():
            self.SetSize(wx.Size(400, 180))

    def Show(self, show=True):
        if not self.IsShown():
            super().Show()
            size = self.GetSize().Get()
            p_size = self.GetParent().GetSize().Get()
            p_pos = self.GetParent().GetPosition()
            self.CenterOnParent()
            self.SetPosition(wx.Point(p_pos.x + p_size[0] - size[0], -1))

    def OnClose(self, event):
        self.Hide()
