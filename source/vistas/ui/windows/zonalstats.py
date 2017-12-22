import math

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
        scroll_panel.SetSizer(scroll_sizer)
        scroll_sizer.Add(self.grid, 1, wx.EXPAND)
        scroll_panel.SetupScrolling()

        self.grid.CreateGrid(1, 2)
        self.grid.SetRowLabelSize(0)
        self.grid.SetColLabelSize(0)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self._data = []

    @staticmethod
    def _format_sig_figs(value, limit):
        """ Format cell values to use significant figures. """
        if not value:
            return '0'
        power = -int(math.floor(math.log10(abs(value)))) + (limit - 1)
        factor = (10 ** power)
        return '{}'.format(round(value * factor) / factor)

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

        column_headings = ['Statistic'] + [x.get('Name') for x in self._data]
        row_headings = [y for y in self._data[0].keys() if y != 'Name']

        # Format the row and column headings
        self.grid.AppendRows(len(row_headings) + 1)
        self.grid.AppendCols(len(column_headings))
        for i, name in enumerate(column_headings):
            self.grid.SetCellValue(0, i, name)
        for i, name in enumerate(row_headings):
            self.grid.SetCellValue(i + 1, 0, name)

        # Populate the table
        sig_figs_limit = 10
        for j, data in enumerate(self._data):
            for i, heading in enumerate(row_headings):
                self.grid.SetCellValue(
                    i + 1, j + 1, self._format_sig_figs(data[heading], sig_figs_limit)
                )

        # Fit the rows/columns
        self.grid.AutoSize()

        # Reset the size of the scrolled window
        size = self.grid.GetSize()
        self.SetClientSize(size)
        self.SetVirtualSize(size)
        self.Fit()

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
