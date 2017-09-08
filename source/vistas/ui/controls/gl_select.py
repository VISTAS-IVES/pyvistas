import os

import wx

from vistas.core.graphics.overlay import BasicOverlayButton
from vistas.core.paths import get_resources_directory
from vistas.ui.events import CameraDragSelectStartEvent


class GLSelectionControls(wx.EvtHandler):
    """ Event handler for initiating drag selection interaction """

    BOX = 'box'
    POLY = 'poly'

    def __init__(self, gl_canvas, camera):
        super().__init__()

        self.camera = camera
        self.canvas = gl_canvas
        self.visible = False

        self.box_select_button = BasicOverlayButton(
            os.path.join(get_resources_directory(), 'images', 'glyphicons-95-vector-path-square.png'), (0, 0)
        )
        self.box_select_button.Bind(wx.EVT_BUTTON, lambda event: self.set_drag_mode(self.BOX))

        self.poly_select_button = BasicOverlayButton(
            os.path.join(get_resources_directory(), 'images', 'glyphicons-97-vector-path-polygon.png'), (0, 0)
        )
        self.poly_select_button.Bind(wx.EVT_BUTTON, lambda event: self.set_drag_mode(self.POLY))

        self.reposition()
        self.show()

        self.canvas.Bind(wx.EVT_SIZE, lambda event: self.reposition())

    def reposition(self):
        height = self.canvas.GetSize().height // 3
        y_offset = 0

        for button in (self.box_select_button, self.poly_select_button):
            button.position = (0, height + y_offset)
            y_offset += 5 + button.size[1]

        self.canvas.Refresh()

    def show(self):
        if not self.visible:
            self.canvas.overlay.add_button(self.box_select_button)
            self.canvas.overlay.add_button(self.poly_select_button)

        self.visible = True

    def hide(self):
        if self.visible:
            self.canvas.overlay.remove_button(self.box_select_button)
            self.canvas.overlay.remove_button(self.poly_select_button)

        self.visible = False

    def set_drag_mode(self, mode):
        wx.PostEvent(self.canvas, CameraDragSelectStartEvent(mode=mode))
