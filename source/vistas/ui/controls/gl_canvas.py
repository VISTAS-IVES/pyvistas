import wx
import wx.glcanvas

from vistas.core.graphics.overlay import Overlay
from vistas.core.observers.camera import CameraObservable
from vistas.core.utils import get_platform
from vistas.ui.controls.gl_camera import GLCameraControls
from vistas.ui.controls.gl_select import GLSelectionControls
from vistas.ui.events import CameraSyncEvent, CameraDragSelectFinishEvent, EVT_CAMERA_DRAG_SELECT_START


class GLCanvas(wx.glcanvas.GLCanvas):
    """
    A panel for rendering an OpenGL context. An OpenGL context is created when the first instance of this class is
    created, and is shared between all other instances.
    """

    initialized = False
    shared_gl_context = None

    def __init__(self, parent, id, camera, attrib_list=None, can_sync=False):
        super().__init__(parent, id, attribList=attrib_list)

        self.overlay = Overlay(self)
        self.camera = camera
        self.camera_controls = GLCameraControls(self, camera)

        self.selection_mode = None
        self.selection_controls = GLSelectionControls(self, camera)

        self.can_sync = can_sync    # Indicate whether this canvas can sync with global interactor

        self.start_x = self.start_y = -1
        self._x = self._y = -1

        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKey)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.Bind(EVT_CAMERA_DRAG_SELECT_START, self.OnCameraDragSelectStart)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        if get_platform() == 'windows':
            self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)

    def OnDestroy(self, event):
        CameraObservable.get().remove_observer(self.camera)
        self.camera_controls.Destroy()
        self.selection_controls.Destroy()

    @property
    def camera_interactor(self):
        return self.camera_controls.camera_interactor

    @camera_interactor.setter
    def camera_interactor(self, interactor):
        self.camera_controls.camera_interactor = interactor

    def Sync(self):
        if self.can_sync and CameraObservable.get().is_sync:
            event = CameraSyncEvent(interactor=self.camera_interactor)
            event.SetEventObject(self)
            wx.PostEvent(self.GetParent().GetParent(), event)

    def OnPaint(self, event):
        if not GLCanvas.initialized:
            GLCanvas.initialized = True
            GLCanvas.shared_gl_context = wx.glcanvas.GLContext(self)
            self.SetCurrent(GLCanvas.shared_gl_context)
            self.SwapBuffers()

        self.SetCurrent(GLCanvas.shared_gl_context)
        self.camera.render(*self.GetSize().Get(), self.overlay)
        self.SwapBuffers()

    def OnEraseBackground(self, event: wx.EraseEvent):
        pass  # Ignore this event to prevent flickering on Windows

    def OnMotion(self, event: wx.MouseEvent):
        if event.LeftIsDown():
            x = event.GetX()
            y = event.GetY()
            if not self.selection_mode and self._x > -1 and self._y > -1:
                self.camera_interactor.mouse_motion(x - self._x, y - self._y, event.ShiftDown(), event.AltDown(),
                                                    event.ControlDown())
            self._x = x
            self._y = y

            if self.selection_mode:
                if self.start_x == -1 and self.start_y == -1:
                    self.start_x = self._x
                    self.start_y = self._y

            self.Sync()
            self.Refresh()
        else:
            self._x = self._y = self.start_x = self.start_y = -1
        event.Skip()

    def OnLeftUp(self, event: wx.MouseEvent):
        if self.selection_mode and self.start_x != -1 and self.start_y != -1:
            if self.start_x <= self._x:
                left = self.start_x
                right = self._x
            else:
                left = self._x
                right = self.start_x

            if self.start_y <= self._y:
                top = self.start_y
                bottom = self._y
            else:
                top = self._y
                bottom = self.start_y

            wx.PostEvent(self.GetParent(),
                         CameraDragSelectFinishEvent(
                             mode=self.selection_mode, left=left, bottom=bottom, right=right,top=top
                         )
                         )
            self.selection_mode = None
        event.Skip()

    def OnMouseWheel(self, event: wx.MouseEvent):
        if self.selection_mode:
            return

        self.camera_interactor.mouse_wheel(event.GetWheelRotation(), event.GetWheelDelta(), event.ShiftDown(),
                                           event.AltDown(), event.ControlDown())
        self._x = self._y = -1
        self.Sync()
        self.Refresh()

    def OnKey(self, event: wx.KeyEvent):
        keycode = event.GetUnicodeKey()
        if keycode != wx.WXK_NONE:
            self.camera_interactor.key_down("{:c}".format(keycode))
            self.Sync()
            self.Refresh()

    def OnCameraDragSelectStart(self, event):
        if event.mode == 'box':
            self.selection_mode = event.mode    # Todo - implement custom polygon drag
        event.Skip()

    def OnPostRedisplay(self, event):
        self.Refresh()
