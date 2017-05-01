import wx


class ListCtrl(wx.ListCtrl):
    def __init__(self, parent, id):
        super().__init__(parent, id)
        self.SetWindowStyle(wx.LC_ICON)
        self.EnableAlternateRowColours()
        self.SetAlternateRowColour(wx.Colour(235, 240, 255))
        # Todo: do we need to incorporate the rest?
