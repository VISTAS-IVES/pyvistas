from vistas.core.color import Color, RGBColor

import wx


class ColorPickerCtrl(wx.BitmapButton):
    def __init__(self, parent, id, color: Color):
        super().__init__(parent, id, wx.Bitmap())
        self.bitmap = wx.Bitmap(20, 20)
        self.SetSize(20, 20)
        self.Bind(wx.EVT_BUTTON, self.OnButton)
        self._color = color
        self.UpdateBitmap()

    def UpdateBitmap(self):
        dc = wx.MemoryDC(self.bitmap)
        dc.Clear()
        self.SetBitmapLabel(self.bitmap)
        self.Refresh()

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value: Color):
        self._color = value
        self.UpdateBitmap()

    def OnButton(self, event):
        color_data = wx.ColourData()
        color_data.SetColour(wx.Colour(*self._color.rgb.rgb_list))
        color_dlg = wx.ColourDialog(self, color_data)
        if color_dlg.ShowModal() == wx.ID_OK:
            wx_color = color_dlg.GetColourData().GetColour()
            self.color = RGBColor(wx_color.Red(), wx_color.Green(), wx_color.Blue())
            evt = wx.ColourPickerEvent(self)
            evt.SetColour(wx_color)
            wx.PostEvent(self, evt)
