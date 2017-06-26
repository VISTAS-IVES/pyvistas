from vistas.core.utils import get_platform
import wx


class StaticImage(wx.Panel):

    def __init__(self, parent, id, image):
        super().__init__(parent, id)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self._image = None
        self.cache = None   # delayed setter
        self.scale = (1, 1)
        self.fit = True
        self.dirty = True

        self.Bind(wx.EVT_PAINT, self.OnPaint)

        # send initial paint event
        self.image = image

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, image):
        self._image = image
        self.dirty = True
        self.Refresh()

    def OnPaint(self, event):

        size = self.GetClientSize()
        dc = wx.BufferedPaintDC(self)
        empty = wx.Bitmap(1, 1)

        if not self.dirty and self.cache.GetWidth() == size.GetWidth() and self.cache.GetHeight() == size.GetHeight():
            dc.DrawBitmap(self.cache, 0, 0)
        else:
            self.cache = wx.Bitmap(size.GetWidth(), size.GetHeight())
            mem_dc = wx.MemoryDC(self.cache)
            mem_dc.SetBrush(wx.Brush(wx.Colour(0, 0, 0)))
            if get_platform() == 'windows':
                mem_dc.SetBackground(wx.Brush(wx.Colour(2, 3, 4)))      # Enable transparency effect
            else:
                mem_dc.SetBackground(wx.Brush(wx.Colour(0, 0, 0, 0)))
            mem_dc.Clear()

            if self.image is not None:
                image = wx.Image(*self.image.size)
                image.SetData(self.image.convert("RGB").tobytes())
                image.SetAlpha(self.image.convert("RGBA").tobytes()[3::4])
                mem_dc.SetUserScale(*self.scale)
                mem_dc.DrawBitmap(wx.Bitmap(image), 0, 0)
                mem_dc.SetUserScale(1.0, 1.0)

            mem_dc.SelectObject(empty)
            dc.DrawBitmap(self.cache, 0, 0)
            self.dirty = False
