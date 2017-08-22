import wx

from vistas.core.graphics.camera_interactor import *
from vistas.core.paths import get_resource_bitmap
from vistas.ui.events import CameraChangedEvent
from vistas.ui.utils import get_main_window, get_paint_dc


class GLCameraButton(wx.Panel):
    SIZE = 24

    def __init__(self, parent, name, y_offset=0, selected=False):
        super().__init__(parent, wx.ID_ANY)

        self.Hide()

        self.frame = wx.Frame(
            wx.GetTopLevelParent(parent), style=wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT | wx.BORDER_NONE
        )
        self.bitmap = get_resource_bitmap(name)
        self.y_offset = y_offset
        self.frame.SetSize(wx.Size(self.SIZE, self.SIZE))
        self.frame.SetPosition(self.screen_position)
        self.frame.Show()

        self.frame.Bind(wx.EVT_PAINT, self.OnPaint)
        self.frame.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
        self.frame.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self.frame.Bind(wx.EVT_LEFT_DOWN, self.OnClick)
        self.Bind(wx.EVT_MOVE, self.OnMove)
        self.Bind(wx.EVT_SIZE, self.OnMove)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

        while parent is not None:
            parent.Bind(wx.EVT_MOVE, self.OnMove)
            parent.Bind(wx.EVT_SIZE, self.OnMove)
            parent = parent.GetParent()

        self.has_mouse = False
        self.selected = selected
        self.frame.SetTransparent(self.alpha)

    @property
    def alpha(self):
        return 200 if self.has_mouse else 100 if self.selected else 50

    @property
    def screen_position(self):
        rect = self.GetParent().GetScreenRect()
        return wx.Point(rect.GetRight() - self.SIZE, rect.GetTop() + self.y_offset)

    def OnDestroy(self, event):
        parent = self.GetParent()
        while parent is not None:
            parent.Unbind(wx.EVT_MOVE)
            parent.Unbind(wx.EVT_SIZE)
            parent = parent.GetParent()
        self.frame.Destroy()
        event.Skip()

    def OnMove(self, event):
        self.frame.SetPosition(self.screen_position)
        event.Skip()

    def OnPaint(self, event):
        dc = get_paint_dc(self.frame)
        dc.Clear()
        dc.DrawBitmap(self.bitmap, 1, 1, True)
        self.frame.SetTransparent(self.alpha)

    def OnEnter(self, event):
        self.has_mouse = True
        self.frame.Refresh()

    def OnLeave(self, event):
        self.has_mouse = False
        self.frame.Refresh()

    def OnClick(self, event):
        if not self.selected:
            wx.PostEvent(self, event)


class GLCameraControls(wx.EvtHandler):
    """
    Event handler for controlling the camera interaction for a GLCanvas. Allows a user to switch between different
    camera interaction modes.
    """

    SPHERE = 0
    FREELOOK = 1
    PAN = 2

    def __init__(self, gl_canvas, camera):
        super().__init__()
        self.camera = camera
        self.sphere_button = GLCameraButton(gl_canvas, "glyphicons-372-global.png", selected=True)
        self.freelook_button = GLCameraButton(gl_canvas, "glyphicons-52-eye-open.png", y_offset=30)
        self.pan_button = GLCameraButton(gl_canvas, "glyphicons-187-move.png", y_offset=60)

        self.sphere_button.Bind(wx.EVT_LEFT_DOWN, self.SelectSphere)
        self.freelook_button.Bind(wx.EVT_LEFT_DOWN, self.SelectFreelook)
        self.pan_button.Bind(wx.EVT_LEFT_DOWN, self.SelectPan)

        self.camera_interactor = SphereInteractor(camera=self.camera)

        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

    def OnDestroy(self, event):
        self.sphere_button.Destroy()
        self.freelook_button.Destroy()
        self.pan_button.Destroy()
        event.Skip()

    def Show(self, show=True):
        self.sphere_button.frame.Show(show)
        self.freelook_button.frame.Show(show)
        self.pan_button.frame.Show(show)

    def Hide(self):
        self.Show(show=False)

    def Reset(self):
        self.SetType(self.camera_interactor.camera_type, False)

    def Refresh(self):
        self.sphere_button.frame.Refresh()
        self.freelook_button.frame.Refresh()
        self.pan_button.frame.Refresh()

    def SelectSphere(self, event):
        self.sphere_button.selected = True
        self.freelook_button.selected = False
        self.pan_button.selected = False
        self.SetType(CameraInteractor.SPHERE)

    def SelectFreelook(self, event):
        self.sphere_button.selected = False
        self.freelook_button.selected = True
        self.pan_button.selected = False
        self.SetType(CameraInteractor.FREELOOK)

    def SelectPan(self, event):
        self.sphere_button.selected = False
        self.freelook_button.selected = False
        self.pan_button.selected = True
        self.SetType(CameraInteractor.PAN)

    def SetType(self, interactor, send_event=True):
        args = {'camera': self.camera, 'reset_mv': False}
        if interactor == CameraInteractor.SPHERE:
            self.camera_interactor = SphereInteractor(**args)
        elif interactor == CameraInteractor.FREELOOK:
            self.camera_interactor = FreelookInteractor(**args)
        elif interactor == CameraInteractor.PAN:
            self.camera_interactor = PanInteractor(**args)
        if send_event:
            wx.PostEvent(get_main_window(), CameraChangedEvent())
        self.Refresh()
