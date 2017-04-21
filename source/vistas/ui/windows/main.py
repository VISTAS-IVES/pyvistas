import wx


class MainWindow(wx.Frame):
    def __init__(self, parent, id):
        super().__init__(parent, id, "VISTAS")

        self.SetSize(1200, 800)
        self.CenterOnScreen()

        
