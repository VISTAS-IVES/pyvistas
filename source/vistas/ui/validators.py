import wx


class FloatValidator(wx.Validator):

    def Clone(self):
        return FloatValidator()

    def Validate(self, win):
        text_ctrl = self.GetWindow()
        num_string = text_ctrl.GetValue()
        try:
            float(num_string)
        except:
            text_ctrl.SetValue("0.0")
            return False
        return True

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True
