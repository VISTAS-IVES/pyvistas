import wx
import wx.glcanvas

from vistas.core.graphics.overlay import Overlay
from vistas.core.observers.camera import CameraObservable
from vistas.core.utils import get_platform
from vistas.ui.controls.gl_camera import GLCameraControls
from vistas.ui.controls.gl_select import GLSelectionControls
from vistas.ui.events import CameraSyncEvent, CameraSelectFinishEvent, EVT_CAMERA_SELECT_MODE


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
        self.last_selection_mode = None
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
        self.Bind(EVT_CAMERA_SELECT_MODE, self.OnCameraSelectMode)

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

            if self.selection_mode and self.selection_mode is GLSelectionControls.BOX:
                    if self.start_x == -1 and self.start_y == -1:
                        self.start_x = self._x
                        self.start_y = self._y
                    self.camera.box_select.from_screen_coords((self.start_x, self.start_y), (self._x, self._y))

            self.Sync()
            self.Refresh()
        else:
            self._x = self._y = self.start_x = self.start_y = -1
        event.Skip()

    def OnLeftUp(self, event: wx.MouseEvent):
        if self.selection_mode and self.start_x != -1 and self.start_y != -1:
            if self.selection_mode is GLSelectionControls.BOX:
                points = self.camera.box_select.coords
                plugin = self.camera.box_select.plugin
                select_event = CameraSelectFinishEvent(mode=self.selection_mode, points=points, plugin=plugin)
                wx.PostEvent(self.GetParent(), select_event)
                self.selection_mode = None
                self.selection_controls.hide_optional_buttons()
            self.Refresh()
        event.Skip()

    def OnLeftDown(self, event: wx.MouseEvent):
        if self.selection_mode and self.selection_mode is GLSelectionControls.POLY:

            # Edge case where the user clicked on the overlay while in POLY mode
            for button in self.overlay.buttons:
                pos = button.position
                size = button.size
                hit_x = pos[0] <= event.GetX() <= pos[0] + size[0]
                hit_y = pos[1] <= event.GetY() <= pos[1] + size[1]
                if hit_x and hit_y:
                    event.Skip()
                    return

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

            # Allow escaping from selection mode
            if keycode == wx.WXK_ESCAPE:
                self.selection_mode = None
                self.camera.poly_select.reset()
                self.camera.box_select.reset()
                self.selection_controls.set_mode(self.selection_controls.CANCEL)

            # Allow point removal from polygon selection
            elif self.selection_mode == GLSelectionControls.POLY and \
                    any((keycode == wx.WXK_BACK, keycode == wx.WXK_DELETE, keycode == wx.WXK_NUMPAD_DELETE)):
                self.camera.poly_select.remove_last()

            elif keycode == wx.WXK_RETURN or keycode == wx.WXK_NUMPAD_ENTER:
                self.selection_controls.set_mode(self.selection_controls.CONFIRM)

            self.Refresh()

    def OnCameraSelectMode(self, event):
        if event.mode in (GLSelectionControls.BOX, GLSelectionControls.POLY):
            self.camera.box_select.reset()
            self.camera.poly_select.reset()
            self.selection_mode = self.last_selection_mode = event.mode
            self.selection_controls.show_optional_buttons()

        elif event.mode is GLSelectionControls.CONFIRM:
            if GLSelectionControls.POLY in (self.selection_mode, self.last_selection_mode):
                points = self.camera.poly_select.coords
                plugin = self.camera.poly_select.plugin
                self.camera.poly_select.close_loop()
                select_event = CameraSelectFinishEvent(mode=self.selection_mode, points=points, plugin=plugin)
                wx.PostEvent(self.GetParent(), select_event)
                self.selection_mode = None
                self.selection_controls.hide_optional_buttons()

        elif event.mode is GLSelectionControls.CANCEL:
            if any(x is not None for x in (self.selection_mode, self.last_selection_mode)):
                self.selection_mode = None
                self.camera.poly_select.reset()
                self.camera.box_select.reset()
            self.selection_controls.hide_optional_buttons()

        elif event.mode is GLSelectionControls.PAUSE:
            self.selection_mode = None

        elif event.mode is GLSelectionControls.RESUME:
            self.selection_mode = self.last_selection_mode

    def OnPostRedisplay(self, event):
        self.Refresh()
