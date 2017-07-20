import wx

from vistas.core.graphics.camera_interactor import *
from vistas.core.paths import get_resource_bitmap
from vistas.ui.controls.static_bitmap_button import StaticBitmapButton
from vistas.ui.events import CameraChangedEvent
from vistas.ui.utils import get_main_window


class GLCameraButtonFrame(wx.Frame):
    BRIGHT = 1
    DARK = 75

    def __init__(self, parent):
        super().__init__(parent, style=wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT)
        self.alpha = self.DARK
        self._selected = False

        self.SetTransparent(self.alpha)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        self._selected = value
        if value:
            self.alpha = self.BRIGHT
        else:
            self.alpha = self.DARK
        self.Refresh()

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self)
        dc.Clear()
        dc.SetBrush(wx.BLACK_BRUSH)
        dc.DrawRectangle(0, 0, *self.GetSize().Get())
        self.SetTransparent(self.alpha)

    def OnEnter(self, event):
        self.alpha = self.BRIGHT
        self.Refresh()

    def OnLeave(self, event):
        if self.selected:
            self.alpha = self.BRIGHT
        else:
            self.alpha = self.DARK
        self.Refresh()


class GLCameraButton(wx.Frame):
    def __init__(self, controls, parent, id, bitmap_path):
        super().__init__(parent, id, style=wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT)
        bitmap = get_resource_bitmap(bitmap_path)
        self.SetSize(wx.Size(bitmap.GetWidth() + 4, bitmap.GetHeight() + 4))
        self.frame = GLCameraButtonFrame(self)
        self.frame.SetSize(self.GetSize())
        self.SetTransparent(100)
        self.Show()
        self.frame.Show()
        main_panel = wx.Panel(self)
        main_panel.SetSize(self.GetSize())
        self.button = StaticBitmapButton(main_panel, id, bitmap, size=self.GetSize())
        self.offset = 0
        self.controls = controls

        self.frame.Bind(wx.EVT_LEFT_DOWN, self.OnClick)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

        while parent is not None:
            wx.GetTopLevelParent(parent).Bind(wx.EVT_MOVE, self.OnMove)
            wx.GetTopLevelParent(parent).Bind(wx.EVT_PAINT, self.OnPaint)
            parent = parent.GetParent()

    def OnDestroy(self, event):
        parent = self.GetParent()
        while parent is not None:
            top = wx.GetTopLevelParent(parent)
            if top is not None:
                top.Unbind(wx.EVT_MOVE)
                top.Unbind(wx.EVT_PAINT)
            parent = parent.GetParent()
        event.Skip()

    def Select(self, select=True):
        self.frame.selected = select
        self.frame.Refresh()

    def OnPaint(self, event):
        self.Reposition()
        event.Skip()

    def OnMove(self, event):
        self.Reposition()
        event.Skip()

    def OnClick(self, event):
        if not self.frame.selected:
            self.controls.SetType(self.GetId())

    def Reposition(self):
        canvas_pos = self.GetParent().GetScreenPosition()
        canvas_size = self.GetParent().GetSize()
        x = canvas_pos.x + canvas_size.x - self.GetSize().x
        y = canvas_pos.y + 10 + self.offset
        pos = wx.Point(x, y)
        self.SetPosition(pos)
        self.frame.SetPosition(pos)
        self.Refresh()
        self.frame.Refresh()


class GLCameraControls(wx.EvtHandler):

    SPHERE = 0
    FREELOOK = 1
    PAN = 2

    def __init__(self, gl_canvas, camera):
        super().__init__()
        self.camera = camera
        self.sphere_button = GLCameraButton(self, gl_canvas, self.SPHERE, "glyphicons-372-global.png")
        y_offset = self.sphere_button.GetSize().y + 5
        self.freelook_button = GLCameraButton(self, gl_canvas, self.FREELOOK, "glyphicons-52-eye-open.png")
        self.freelook_button.offset = y_offset
        y_offset += self.freelook_button.GetSize().y + 5
        self.pan_button = GLCameraButton(self, gl_canvas, self.PAN, "glyphicons-187-move.png")
        self.pan_button.offset = y_offset

        self.camera_interactor = SphereInteractor(camera=self.camera)

        self.sphere_button.Select()
        self.sphere_button.frame.Refresh()

    def Show(self, show=True):
        self.sphere_button.frame.Show(show)
        self.sphere_button.Show(show)
        self.freelook_button.frame.Show(show)
        self.freelook_button.Show(show)
        self.pan_button.frame.Show(show)
        self.pan_button.Show(show)

    def Hide(self):
        self.Show(show=False)

    def Reset(self):
        self.SetType(self.camera_interactor.camera_type, False)

    def RepositionAll(self):
        self.sphere_button.Reposition()
        self.freelook_button.Reposition()
        self.pan_button.Reposition()

    def SetType(self, id, send_event=True):

        args = {'camera': self.camera, 'reset_mv': False}
        if id == self.SPHERE or id == CameraInteractor.SPHERE:
            self.sphere_button.Select()
            self.camera_interactor = SphereInteractor(**args)
            self.freelook_button.Select(False)
            self.pan_button.Select(False)
        elif id == self.FREELOOK or id == CameraInteractor.FREELOOK:
            self.freelook_button.Select()
            self.camera_interactor = FreelookInteractor(**args)
            self.sphere_button.Select(False)
            self.pan_button.Select(False)
        elif id == self.PAN or id == CameraInteractor.PAN:
            self.pan_button.Select()
            self.camera_interactor = PanInteractor(**args)
            self.sphere_button.Select(False)
            self.freelook_button.Select(False)

        if send_event:
            wx.PostEvent(get_main_window(), CameraChangedEvent())
