import os

import wx

from vistas.core.graphics.overlay import BasicOverlayButton
from vistas.core.paths import get_resources_directory
from vistas.ui.events import CameraSelectModeEvent


class GLSelectionControls(wx.EvtHandler):
    """ Event handler for initiating selection interaction """

    BOX = 'box'
    POLY = 'poly'
    CONFIRM = 'confirm'
    CANCEL = 'cancel'

    def __init__(self, gl_canvas, camera):
        super().__init__()

        self.camera = camera
        self.canvas = gl_canvas
        self.visible = False
        self.optional_buttons_visible = False
        self.last_mode = None

        self.box_select_button = BasicOverlayButton(
            os.path.join(get_resources_directory(), 'images', 'glyphicons-95-vector-path-square.png'), (0, 0)
        )
        self.box_select_button.Bind(wx.EVT_BUTTON, lambda event: self.set_mode(self.BOX))

        self.poly_select_button = BasicOverlayButton(
            os.path.join(get_resources_directory(), 'images', 'glyphicons-97-vector-path-polygon.png'), (0, 0)
        )
        self.poly_select_button.Bind(wx.EVT_BUTTON, lambda event: self.set_mode(self.POLY))
        self.cancel_button = BasicOverlayButton(
            os.path.join(get_resources_directory(), 'images', 'glyphicons-193-remove-sign.png'), (0, 0)
        )
        self.cancel_button.Bind(wx.EVT_BUTTON, lambda event: self.set_mode(self.CANCEL))
        self.confirm_button = BasicOverlayButton(
            os.path.join(get_resources_directory(), 'images', 'glyphicons-194-ok-sign.png'), (0, 0)
        )
        self.confirm_button.Bind(wx.EVT_BUTTON, lambda event: self.set_mode(self.CONFIRM))

        self.reposition()
        self.show()

        self.canvas.Bind(wx.EVT_SIZE, lambda event: self.reposition())

    def reposition(self):
        size = self.canvas.GetSize()
        width = size.width
        height = size.height // 3
        y_offset = 0

        for button in (self.box_select_button, self.poly_select_button, self.cancel_button, self.confirm_button):
            button.position = (width - button.size[0], height + y_offset)
            y_offset += 5 + button.size[1]

        self.canvas.Refresh()

    def show_optional_buttons(self):
        if not self.optional_buttons_visible:
            self.canvas.overlay.add_button(self.cancel_button)
            self.canvas.overlay.add_button(self.confirm_button)
            self.optional_buttons_visible = True

    def hide_optional_buttons(self):
        if self.optional_buttons_visible:
            self.canvas.overlay.remove_button(self.cancel_button)
            self.canvas.overlay.remove_button(self.confirm_button)
            self.optional_buttons_visible = False

    def show(self):
        if not self.visible:
            self.canvas.overlay.add_button(self.box_select_button)
            self.canvas.overlay.add_button(self.poly_select_button)
            if self.last_mode in (self.BOX, self.POLY):
                self.show_optional_buttons()

        self.visible = True

    def hide(self):
        if self.visible:
            self.canvas.overlay.remove_button(self.box_select_button)
            self.canvas.overlay.remove_button(self.poly_select_button)
            self.hide_optional_buttons()

        self.visible = False

    def set_mode(self, mode):
        wx.PostEvent(self.canvas, CameraSelectModeEvent(mode=mode))
