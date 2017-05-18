import wx


class ExceptionDialog(wx.Dialog):
    is_shown = False

    def __init__(self, parent, message):
        super().__init__(parent, wx.ID_ANY)

        self.SetSize((600, 400))

        main_panel = wx.Panel(self, wx.ID_ANY)
        label = wx.StaticText(main_panel, wx.ID_ANY, 'An unhandled exception occurred:')
        text = wx.TextCtrl(main_panel, wx.ID_ANY, message, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)

        button = wx.Button(main_panel, wx.ID_ANY, 'Ok')
        button.SetDefault()

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)

        main_sizer.Add(main_panel, 1, wx.EXPAND)

        main_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        main_panel.SetSizer(main_panel_sizer)

        main_panel_sizer.Add(label, 0, wx.LEFT | wx.TOP | wx.RIGHT, 5)
        main_panel_sizer.Add(text, 1, wx.EXPAND | wx.ALL, 5)
        main_panel_sizer.Add(button, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.BOTTOM | wx.RIGHT, 5)

        button.Bind(wx.EVT_BUTTON, self.OnOk)

        self.Layout()
        self.CenterOnParent()

    def OnOk(self, event):
        self.Close()

    def ShowModal(self):
        if ExceptionDialog.is_shown:
            return False

        try:
            ExceptionDialog.is_shown = True
            return super().ShowModal()
        finally:
            ExceptionDialog.is_shown = False
