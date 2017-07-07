import wx
import wx.grid


class InspectWindow(wx.Frame):
    def __init__(self, parent, id):
        super().__init__(parent, id, "Inspect", style=wx.FRAME_TOOL_WINDOW | wx.SYSTEM_MENU | wx.CAPTION | wx.CLOSE_BOX
                                                      | wx.FRAME_FLOAT_ON_PARENT | wx.RESIZE_BORDER)
        self.SetSize(200, 450)
        main_panel = wx.Panel(self, wx.ID_ANY)
        self.grid = wx.grid.Grid(main_panel, wx.ID_ANY)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        main_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        main_panel.SetSizer(main_panel_sizer)
        main_panel_sizer.Add(self.grid, 1, wx.EXPAND)

        sizer.Add(main_panel, 1, wx.EXPAND)
        self.grid.CreateGrid(1, 2)
        self.grid.SetRowLabelSize(0)
        self.grid.SetColLabelSize(0)

        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self._data = {}

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value
        num_rows = self.grid.GetNumberRows()
        if num_rows:
            self.grid.DeleteRows(0, num_rows)

        if self._data is None:
            return

        self.grid.AppendRows(len(self._data.keys()))

        i = 0
        for key, val in self._data.items():
            self.grid.SetCellValue(i, 0, key)
            self.grid.SetCellValue(i, 1, str(self._data[key]))
            i += 1

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
