import wx
import wx.glcanvas

from vistas.core.utils import get_platform
from vistas.core.graphics.camera_interactor import SphereInteractor

from OpenGL.GL import *


class GLCanvas(wx.glcanvas.GLCanvas):
    initialized = False
    shared_gl_context = None

    def __init__(self, parent, id, camera, attrib_list=None):
        super().__init__(parent, id, attribList=attrib_list)

        self.camera = camera
        self.camera_interactor = SphereInteractor(self.camera)
        self._x = self._y = -1

        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKey)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        if get_platform() == 'windows':
            self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        # Todo: VI_EVENT_REDISPLAY

        # self.SetFocus()  # Crashes on Mac

    def OnPaint(self, event):
        if not GLCanvas.initialized:
            GLCanvas.initialized = True
            GLCanvas.shared_gl_context = wx.glcanvas.GLContext(self)
            self.SetCurrent(GLCanvas.shared_gl_context)
            self.SwapBuffers()

        size = self.GetSize()
        dc = wx.PaintDC(self)

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

    def OnMouseWheel(self, event: wx.MouseEvent):
        self.camera_interactor.mouse_wheel(event.GetWheelRotation(), event.ShiftDown(), event.AltDown(),
                                           event.ControlDown())
        self._x = self._y = -1
        self.Refresh()

    def OnKey(self, event: wx.KeyEvent):
        keycode = event.GetKeyCode()
        if keycode < 256 and keycode >= 28:
            self.camera_interactor.key_down(keycode)
            self.Refresh()

    def OnPostRedisplay(self, event):
        self.Refresh()
