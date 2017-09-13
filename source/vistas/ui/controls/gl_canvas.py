import wx
import wx.glcanvas

from vistas.core.graphics.overlay import Overlay
from vistas.core.graphics.simple import Box
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
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
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

    @property
    def mouse_box_coords(self):
        return dict(start=(self.start_x, self.start_y), current=(self._x, self._y))

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
                if self.selection_mode == 'box':
                    if self.start_x == -1 and self.start_y == -1:
                        self.start_x = self._x
                        self.start_y = self._y
                    self.camera.box_select.from_screen_coords(**self.mouse_box_coords)
                elif self.selection_mode == 'poly':
                    pass    # Update leading line in the poly select

            self.Sync()
            self.Refresh()
        else:
            self._x = self._y = self.start_x = self.start_y = -1
        event.Skip()

    def OnLeftUp(self, event: wx.MouseEvent):
        if self.selection_mode and self.start_x != -1 and self.start_y != -1:
            if self.selection_mode == 'box':
                select_event = CameraDragSelectFinishEvent(mode=self.selection_mode)    # Todo - this needs to send the 3D point coordinates, not the screen coordinates!!!
                coords = self.mouse_box_coords
                select_event.left = coords.get('left')
                select_event.bottom = coords.get('bottom')
                select_event.right = coords.get('right')
                select_event.top = coords.get('top')
                self.camera.box_select.drawing = False
                #wx.PostEvent(self.GetParent(), select_event)
                self.selection_mode = None
            self.Refresh()
        event.Skip()

    def OnLeftDown(self, event: wx.MouseEvent):
        if self.selection_mode:
            if self.selection_mode == 'poly':
                self.camera.poly_select.append_point(event.GetX(), event.GetY())
                self.Refresh()

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

            # Todo - if in selection mode, allow 'esc' to cancel editing
            # Todo - if selection mode is 'poly', let 'delete', and 'backspace' remove the last created point

            self.Refresh()

    def OnCameraDragSelectStart(self, event):
        if event.mode in (GLSelectionControls.BOX, GLSelectionControls.POLY):
            if self.selection_mode is not None:
                self.camera.box_select.reset()
                self.camera.poly_select.reset()
            self.selection_mode = event.mode
            if self.selection_mode == 'box':
                self.camera.box_select.reset()
            else:
                self.camera.poly_select.reset()

        elif event.mode == GLSelectionControls.CONFIRM:
            if self.selection_mode is not None and self.selection_mode == 'poly':
                self.camera.poly_select.remove_last()
                points = self.camera.poly_select.screen_coords      # Todo - this needs to pass the 3D positions, not the screen coordinates!!!
                select_event = CameraDragSelectFinishEvent(mode=self.selection_mode, points=points)
                #wx.PostEvent(self.GetParent(), select_event)
                self.selection_mode = None

        elif event.mode == GLSelectionControls.CANCEL:
            if self.selection_mode is not None:
                self.selection_mode = None

        event.Skip()

    def OnPostRedisplay(self, event):
        self.Refresh()
