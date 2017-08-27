import os

import wx

from vistas.core.graphics.camera_interactor import *
from vistas.core.graphics.overlay import BasicOverlayButton
from vistas.core.paths import get_resources_directory
from vistas.ui.events import CameraChangedEvent
from vistas.ui.utils import get_main_window


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
        self.canvas = gl_canvas
        self.visible = False

        self.sphere_button = BasicOverlayButton(
            os.path.join(get_resources_directory(), 'images', 'glyphicons-372-global.png'), (0, 0)
        )
        self.sphere_button.opaque = True
        self.freelook_button = BasicOverlayButton(
            os.path.join(get_resources_directory(), 'images', 'glyphicons-52-eye-open.png'), (0, 0)
        )
        self.pan_button = BasicOverlayButton(
            os.path.join(get_resources_directory(), 'images', 'glyphicons-187-move.png'), (0, 0)
        )

        self.camera_interactor = SphereInteractor(camera=self.camera)

        self.reposition()
        self.show()

        self.canvas.Bind(wx.EVT_SIZE, lambda event: self.reposition())
        self.sphere_button.Bind(wx.EVT_BUTTON, lambda event: self.set_type(self.SPHERE))
        self.freelook_button.Bind(wx.EVT_BUTTON, lambda event: self.set_type(self.FREELOOK))
        self.pan_button.Bind(wx.EVT_BUTTON, lambda event: self.set_type(self.PAN))

    def reset(self):
        self.set_type(self.camera_interactor.camera_type, False)

    def reposition(self):
        width = self.canvas.GetSize().width

        y_offset = 10

        for button in (self.sphere_button, self.freelook_button, self.pan_button):
            button.position = (width - button.size[0], y_offset)
            y_offset += 5 + button.size[1]

        self.canvas.Refresh()

    def show(self):
        if not self.visible:
            self.canvas.overlay.add_button(self.sphere_button)
            self.canvas.overlay.add_button(self.freelook_button)
            self.canvas.overlay.add_button(self.pan_button)

        self.visible = True

    def hide(self):
        if self.visible:
            self.canvas.overlay.remove_button(self.sphere_button)
            self.canvas.overlay.remove_button(self.freelook_button)
            self.canvas.overlay.remove_button(self.pan_button)

        self.visible = False

    def set_type(self, interactor, send_event=True):
        self.sphere_button.opaque = False
        self.freelook_button.opaque = False
        self.pan_button.opaque = False

        if interactor in (self.SPHERE, CameraInteractor.SPHERE):
            self.sphere_button.opaque = True
            self.camera_interactor = SphereInteractor(self.camera, False)

        elif interactor in (self.FREELOOK, CameraInteractor.FREELOOK):
            self.freelook_button.opaque = True
            self.camera_interactor = FreelookInteractor(self.camera, False)

        elif interactor in (self.PAN, CameraInteractor.PAN):
            self.pan_button.opaque = True
            self.camera_interactor = PanInteractor(self.camera, False)

        self.canvas.Refresh()

        if send_event:
            wx.PostEvent(get_main_window(), CameraChangedEvent())
