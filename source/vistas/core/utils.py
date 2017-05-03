import platform
import wx


def get_platform():
    return 'macos' if platform.uname().system == 'Darwin' else 'windows'


def get_transparent_paint_dc(win):
    if get_platform() == 'windows':
        dc = wx.BufferedPaintDC(win)
        dc.SetBrush(wx.Brush((win if win.UseBgCol() else win.GetParent()).GetBackgroundColour()))
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(0, 0, *win.GetSize().Get())
    else:
        dc = wx.PaintDC(win)
    return dc
