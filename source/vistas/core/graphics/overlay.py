import os
from PIL import Image

import numpy
import wx
from OpenGL.GL import *

from vistas.core.graphics.mesh import Mesh
from vistas.core.graphics.shader import ShaderProgram
from vistas.core.graphics.texture import Texture
from vistas.core.paths import get_resources_directory


class Overlay:
    """ A 2D overlay of UI buttons rendered on top of the scene """

    def __init__(self, canvas):
        self._buttons = []

        self.mesh = None
        self.needs_mesh_update = True

        self.sprite = None
        self.needs_sprite_update = True

        self.canvas = canvas
        self.target = None

        canvas.Bind(wx.EVT_MOTION, self.on_canvas_motion)
        canvas.Bind(wx.EVT_LEAVE_WINDOW, self.on_canvas_leave)
        canvas.Bind(wx.EVT_LEFT_DOWN, self.on_canvas_click)

    def reset(self):
        self.mesh = None
        self.needs_mesh_update = True
        self.sprite = None
        self.needs_sprite_update = True

    def generate_sprite(self):
        width = max(x.size[0] for x in self._buttons)
        height = sum(x.size[1] * 3 for x in self._buttons)

        im = Image.new('RGBA', (width, height), (0, 0, 0, 0))

        def make_uv(y, size):
            """ Returns uv coords to match the mesh vertices for a button """

            return 0, y/height, size[0]/width, y/height, 0, (y+size[1])/height, size[0]/width, (y+size[1])/height

        y_offset = 0
        for button in self._buttons:
            uv = []

            for attr in ('default_image', 'hover_image'):
                uv.append(make_uv(y_offset, button.size))

                image = getattr(button, attr)

                if image is not None:
                    im.paste(image, (0, y_offset, button.size[0], y_offset + button.size[1]))

                y_offset += button.size[1]

            button.uv = uv

        self.sprite = Texture(im, src_format=GL_RGBA, gl_format=GL_RGBA)

        self.needs_sprite_update = False
        self.needs_mesh_update = True

    def generate_mesh(self):
        num_indices = 6 * len(self._buttons)
        num_vertices = 4 * len(self._buttons)

        if self.mesh is None:
            self.mesh = Mesh(num_indices, num_vertices, has_texture_coords=True, mode=Mesh.TRIANGLES)
            self.mesh.shader = ShaderProgram()
            self.mesh.shader.attach_shader(
                os.path.join(get_resources_directory(), 'shaders', 'overlay_vert.glsl'), GL_VERTEX_SHADER
            )
            self.mesh.shader.attach_shader(
                os.path.join(get_resources_directory(), 'shaders', 'overlay_frag.glsl'), GL_FRAGMENT_SHADER
            )

        # Create new mesh if buttons are added or removed; otherwise can use existing buffers
        if self.mesh.num_indices != num_indices or self.mesh.num_vertices != num_vertices:
            self.mesh = None
            return self.generate_mesh()

        self.mesh.vertices = numpy.array([
            [
                x.position[0], x.position[1], 0,
                x.position[0]+x.size[0], x.position[1], 0,
                x.position[0], x.position[1]+x.size[1], 0,
                x.position[0]+x.size[0], x.position[1]+x.size[1], 0
            ] for x in self._buttons
        ], dtype=numpy.float32)

        self.mesh.indices = numpy.array([
            [
                i, i+1, i+2,
                i+1, i+2, i+3
            ] for i in (x*4 for x in range(len(self._buttons)))
        ])

        self.mesh.texcoords = numpy.array([x.uv[0] if x.state == x.DEFAULT else x.uv[1] for x in self._buttons])

        self.needs_mesh_update = False

    def add_button(self, button):
        button.overlay = self
        self._buttons.append(button)
        self.reset()

    def remove_button(self, button):
        if button in self._buttons:
            self._buttons.remove(button)
            self.reset()

    def render(self, width, height):
        if not self._buttons:
            return

        if self.needs_sprite_update:
            self.generate_sprite()

        if self.needs_mesh_update:
            self.generate_mesh()

        self.mesh.shader.link_program()

        glDisable(GL_DEPTH_TEST)
        glViewport(0, 0, width, height)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glUseProgram(self.mesh.shader.program)
        glBindVertexArray(self.mesh.vertex_array_object)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.sprite.texture)
        self.mesh.shader.uniform1i('overlay', 0)
        self.mesh.shader.uniform1f('width', width)
        self.mesh.shader.uniform1f('height', height)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.mesh.index_buffer)

        glDrawElements(GL_TRIANGLES, self.mesh.num_indices, GL_UNSIGNED_INT, None)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        glBindTexture(GL_TEXTURE_2D, 0)
        glUseProgram(0)
        glDisable(GL_BLEND)

    def on_canvas_motion(self, event):
        for button in reversed(self._buttons):
            contains = (
                button.position[0] <= event.x <= button.position[0] + button.size[0] and
                button.position[1] <= event.y <= button.position[1] + button.size[1]
            )

            if contains:
                if button is self.target:
                    return

                self.target = button

                wx.PostEvent(button, wx.MouseEvent(wx.wxEVT_ENTER_WINDOW))
                return

        if self.target:
            wx.PostEvent(self.target, wx.MouseEvent(wx.wxEVT_LEAVE_WINDOW))
            self.target = None

        event.Skip()

    def on_canvas_leave(self, event):
        if self.target:
            wx.PostEvent(self.target, wx.MouseEvent(wx.wxEVT_LEAVE_WINDOW))
            self.target = None

        event.Skip()

    def on_canvas_click(self, event):
        if not self.target:
            event.Skip()
            return

        wx.PostEvent(self.target, wx.MouseEvent(wx.wxEVT_LEFT_DOWN))


class Button(wx.EvtHandler):
    """ A button to be drawn on the overlay """

    DEFAULT = 'default'
    HOVER = 'hover'

    def __init__(self, position, size, default_image, hover_image=None):
        super().__init__()

        self.overlay = None
        self.uv = None
        self.state = self.DEFAULT

        self._position = position
        self._size = size
        self._default_image = None
        self._hover_image = None

        self.default_image = default_image
        self.hover_image = hover_image or default_image

        self.Bind(wx.EVT_ENTER_WINDOW, self.on_mouse_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_mouse_leave)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_mouse_click)

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, position):
        if self._position == position:
            return

        self._position = position
        if self.overlay:
            self.overlay.needs_mesh_update = True

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, size):
        if self._size == size:
            return

        self._size = size
        if self.overlay:
            self.overlay.needs_mesh_update = True

    @property
    def default_image(self):
        return self._default_image

    @default_image.setter
    def default_image(self, image):
        if image is self._default_image:
            return

        self._default_image = image
        if self.overlay:
            self.overlay.reset()

    @property
    def hover_image(self):
        return self._hover_image

    @hover_image.setter
    def hover_image(self, image):
        if image is self._hover_image:
            return

        self._hover_image = image
        if self.overlay:
            self.overlay.reset()

    def on_mouse_enter(self, event):
        self.state = self.HOVER

        if self.overlay:
            self.overlay.needs_mesh_update = True

        self.overlay.canvas.Refresh()

    def on_mouse_leave(self, event):
        self.state = self.DEFAULT

        if self.overlay:
            self.overlay.needs_mesh_update = True

        self.overlay.canvas.Refresh()

    def on_mouse_click(self, event):
        wx.PostEvent(self, wx.CommandEvent(wx.wxEVT_BUTTON))


class BasicOverlayButton(Button):
    """ Standard overlay button, partially transparent with more opaque hover mode """

    def __init__(self, path_or_image, position):
        self._opaque = False

        if isinstance(path_or_image, Image.Image):
            image = path_or_image
        else:
            image = Image.open(path_or_image)

        super().__init__(position, image.size, image, image)

        self.original_image = image
        self.default_image = image

    @Button.default_image.setter
    def default_image(self, image):
        self.original_image = image

        image = Image.alpha_composite(Image.new('RGBA', image.size, (255, 255, 255, 100)), image)
        transparency = Image.new('RGBA', image.size, (0, 0, 0, 0))
        image_70 = Image.blend(transparency, image, .7)

        self._default_image = image if self.opaque else image_70
        self.hover_image = image

    @property
    def opaque(self):
        return self._opaque

    @opaque.setter
    def opaque(self, opaque):
        self._opaque = opaque
        self.default_image = self.original_image
