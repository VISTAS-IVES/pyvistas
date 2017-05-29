import os

import wx
import wx.lib.newevent

FileChooserEvent, EVT_FILE_VALUE_CHANGE = wx.lib.newevent.NewEvent()


class FileChooserCtrl(wx.Panel):

    def __init__(self, parent, id):
        super().__init__(parent, id)
        self.SetWindowStyle(wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        self.label = wx.StaticText(self, wx.ID_ANY, "No file selected")
        self.button = wx.Button(self, wx.ID_ANY, "Choose file...")
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(sizer)
        sizer.Add(self.label, 0, wx.TOP, 5)
        sizer.Add(self.button, 0, wx.LEFT, 10)
        self.Fit()
        self.wildcard = "*.*"
        self._file = None

    @property
    def file(self):
        return self._file

    @file.setter
    def file(self, value):
        self._file = value
        label = os.path.abspath(self._file)
        self.label.SetLabel(label)
        self.Fit()

        container_size = self.GetContainingSizer().GetSize()
        overflow = self.GetSize().x - container_size.x
        if overflow > 0:
            target = self.label.GetSize().x - overflow
            dc = wx.MemoryDC()
            while len(label) > 0 and dc.GetTextExtent(label).GetWidth() > target:
                label = label[0:len(label) - 1]
            self.label.SetLabel(label + '...')
            self.Fit()

    def OnClick(self, event):
        fd = wx.FileDialog(self, "Choose a file", "", "", self.wildcard)
        if fd.ShowModal() == wx.ID_OK:
            self.file = fd.GetPath()
            wx.PostEvent(self, FileChooserEvent(path=self._file))

    def ClearFile(self):
        self._file = None
        self.label.SetLabel("No file selected")
        self.Fit()
