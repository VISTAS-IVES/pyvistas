from vistas.core.histogram import Histogram

import wx


class HistogramCtrl(wx.Control):
    def __init__(self, parent, id, histogram=None):
        super().__init__(parent, id)
        if histogram is None:
            histogram = Histogram()
        self.histogram = histogram
        pass    # Todo: Implement
