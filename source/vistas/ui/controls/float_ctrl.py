from string import digits
import wx


FloatCtrlEventBase, EVT_FLOAT = wx.lib.newevent.NewEvent()


class FloatCtrlEvent(FloatCtrlEventBase):
    """ An event that simply passes a float value. """

    def __init__(self, value=None):
        super().__init__(value=value)


class FloatCtrl(wx.TextCtrl):
    """
    A custom text input for handling floating point values. Functions almost exactly like wx.TextCtrl, except values are
    expected to be `float` rather than `str`.
    """

    def __init__(self, parent, id=wx.ID_ANY, value=0.0, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0,
                 validator=wx.DefaultValidator, name='floatctrl'):
        super().__init__(parent, id, value=str(value), pos=pos, size=size, style=style, validator=validator, name=name)

        self.Bind(wx.EVT_TEXT, self.OnText)

    def OnText(self, event):
        value = ''.join(c for c in super().GetValue() if c in digits + '.')
        if not value:
            value = '0'
        self.ChangeValue(value)     # don't send another event

        try:
            wx.PostEvent(self, FloatCtrlEvent(self.GetValue()))
        except ValueError:
            pass
        event.Skip()

    def GetValue(self):
        return float(super().GetValue())

    def SetValue(self, value):
        if not isinstance(value, (float, int)):
            raise ValueError('FloatCtrl requires float values')
        super().SetValue(str(value))
