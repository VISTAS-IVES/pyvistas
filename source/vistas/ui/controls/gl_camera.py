from vistas.core.paths import get_resource_bitmap
from vistas.core.graphics.camera_interactor import *
from vistas.ui.controls.static_bitmap_button import StaticBitmapButton

import wx
import wx.lib.newevent

CameraChangedEvent, EVT_CAMERA_MODE_CHANGED = wx.lib.newevent.NewEvent()


class GLCameraButtonFrame(wx.Frame):
    def __init__(self, parent):
        super().__init__(parent, id=wx.ID_ANY, style=wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT)
        self.alpha = 150
        self._selected = False

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self.SetTransparent(self.alpha)

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        self._selected = value
        if value:
            self.alpha = 50
        else:
            self.alpha = 150
        self.Refresh()

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self)
        dc.Clear()
        dc.SetBrush(wx.BLACK_BRUSH)
        size = self.GetSize().Get()
        dc.DrawRectangle(0, 0, *size)
        self.SetTransparent(self.alpha)

    def OnEnter(self, event):
        self.alpha = 1
        self.Refresh()

    def OnLeave(self, event):
        if self._selected:
            self.alpha = 50
        else:
            self.alpha = 150
        self.Refresh()


class GLCameraButton(wx.Frame):
    def __init__(self, parent, id, icon_name):
        super().__init__(parent, id, style=wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT)
        bitmap = get_resource_bitmap(icon_name)
        self.SetSize(wx.Size(bitmap.GetWidth() + 4, bitmap.GetHeight() + 4))
        self.offset = 0
        self.frame = GLCameraButtonFrame(self)
        self.frame.SetSize(self.GetSize())
        self.SetTransparent(100)
        self.Show()
        self.frame.Show()
        main_panel = wx.Panel(self)
        main_panel.SetSize(self.GetSize())
        self.button = StaticBitmapButton(main_panel, id, bitmap)

        self.frame.Bind(wx.EVT_LEFT_DOWN, self.OnClick)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

        while parent is not None:
            wx.GetTopLevelParent(parent).Bind(wx.EVT_MOVE, self.OnMove)
            wx.GetTopLevelParent(parent).Bind(wx.EVT_PAINT, self.OnPaint)
            parent = parent.GetParent()

    def OnDestroy(self, event):
        parent = self.GetParent()
        while parent is not None:
            wx.GetTopLevelParent(parent).Unbind(wx.EVT_MOVE)
            wx.GetTopLevelParent(parent).Unbind(wx.EVT_PAINT)
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
        evt = wx.CommandEvent()
        evt.SetEventObject(self)
        wx.PostEvent(self, event)
        self.GetParent().SetFocus()

    def Reposition(self):
        canvas_pos = self.GetParent().GetScreenPosition().Get()
        canvas_size = self.GetParent().GetSize().Get()
        x = canvas_pos[0] + canvas_size[0] + self.GetSize().x
        y = canvas_pos[1] + 10 + self.offset
        pos = wx.Point(x, y)
        self.SetPosition(pos)
        self.frame.SetPosition(pos)
        self.Refresh()
        self.frame.Refresh()


class GLCameraControls(wx.EvtHandler):

    CAMERA_DICT = {
        0: CameraInteractor.SPHERE,
        1: CameraInteractor.FREELOOK,
        2: CameraInteractor.PAN
    }

    def __init__(self, gl_canvas, camera):
        super().__init__()
        self.sphere_button = GLCameraButton(gl_canvas, 0, "glyphicons-372-global.png")
        y_offset = self.sphere_button.GetSize().Get()[1]
        self.freelook_button = GLCameraButton(gl_canvas, 1, "glyphicons-52-eye-open.png")
        self.freelook_button.offset = y_offset
        y_offset = y_offset + self.freelook_button.GetSize().Get()[1]
        self.pan_button = GLCameraButton(gl_canvas, 2, "glyphicons-187-move.png")
        self.pan_button.offset = y_offset

        self.sphere_button.Bind(wx.EVT_BUTTON, self.OnCameraButton)
        self.freelook_button.Bind(wx.EVT_BUTTON, self.OnCameraButton)
        self.pan_button.Bind(wx.EVT_BUTTON, self.OnCameraButton)

        self.camera_interactor = SphereInteractor(camera=camera)

        self.sphere_button.Select()
        self.sphere_button.frame.Refresh()

    def OnCameraButton(self, event):
        button = event.GetEventObject()
        if button.frame.selected:
            return
        self.SetType(button.GetId())
        wx.PostEvent(self, CameraChangedEvent())

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
        self.SetType(self.camera_interactor.camera_type)

    def RepositionAll(self):
        self.sphere_button.Reposition()
        self.freelook_button.Reposition()
        self.pan_button.Reposition()

    def SetType(self, camera_type_id):

        camera_type = self.CAMERA_DICT[camera_type_id]
        args = {'camera': self.camera_interactor.camera, 'reset_mv': False}
        if camera_type == CameraInteractor.SPHERE:
            self.sphere_button.Select()
            self.camera_interactor = SphereInteractor(**args)
            self.freelook_button.Select(False)
            self.pan_button.Select(False)
        elif camera_type == CameraInteractor.FREELOOK:
            self.freelook_button.Select()
            self.camera_interactor = FreelookInteractor(**args)
            self.sphere_button.Select(False)
            self.pan_button.Select(False)
        elif camera_type == CameraInteractor.PAN:
            self.pan_button.Select()
            self.camera_interactor = PanInteractor(**args)
            self.sphere_button.Select(False)
            self.freelook_button.Select(False)
