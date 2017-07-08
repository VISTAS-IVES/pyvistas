import wx
import wx.glcanvas

from vistas.core.utils import get_platform
# from vistas.ui.controls.gl_camera import GLCameraControls
from vistas.core.graphics.camera_interactor import SphereInteractor


class GLCanvas(wx.glcanvas.GLCanvas):
    initialized = False
    shared_gl_context = None

    def __init__(self, parent, id, camera, attrib_list=None):
        super().__init__(parent, id, attribList=attrib_list)

        self.camera = camera
        self.camera_interactor = SphereInteractor(camera)
        self._x = self._y = -1

        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKey)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        if get_platform() == 'windows':
            self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)

    def OnPaint(self, event):
        if not GLCanvas.initialized:
            GLCanvas.initialized = True
            GLCanvas.shared_gl_context = wx.glcanvas.GLContext(self)
            self.SetCurrent(GLCanvas.shared_gl_context)
            self.SwapBuffers()

        size = self.GetSize()
        dc = wx.PaintDC(self)   # noqa: F841

        self.SetCurrent(GLCanvas.shared_gl_context)
        self.camera.render(size.GetWidth(), size.GetHeight())
        self.SwapBuffers()

    def OnEraseBackground(self, event: wx.EraseEvent):
        pass  # Ignore this event to prevent flickering on Windows

    def OnMotion(self, event: wx.MouseEvent):
        if event.LeftIsDown():
            x = event.GetX()
            y = event.GetY()
            if self._x > -1 and self._y > -1:
                self.camera_interactor.mouse_motion(x - self._x, y - self._y, event.ShiftDown(), event.AltDown(),
                                                    event.ControlDown())
            self._x = x
            self._y = y
            self.Refresh()
        else:
            self._x = self._y = -1
        event.Skip()

    def OnMouseWheel(self, event: wx.MouseEvent):
        self.camera_interactor.mouse_wheel(event.GetWheelRotation(), event.GetWheelDelta(), event.ShiftDown(),
                                           event.AltDown(), event.ControlDown())
        self._x = self._y = -1
        self.Refresh()

    def OnKey(self, event: wx.KeyEvent):
        keycode = event.GetUnicodeKey()
        if keycode != wx.WXK_NONE:
            self.camera_interactor.key_down("{:c}".format(keycode))
            self.Refresh()

    def OnPostRedisplay(self, event):
        self.Refresh()
