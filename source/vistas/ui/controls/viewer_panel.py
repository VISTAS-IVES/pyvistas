import wx

from vistas.core.paths import get_resource_bitmap


class ViewerPanel(wx.Panel):
    NORTH = 'north'
    EAST = 'east'
    SOUTH = 'south'
    WEST = 'west'

    def __init__(self, parent, id):
        super().__init__(parent, id)

        self.north = []
        self.east = None
        self.south = []
        self.west = None
        self.width = 1.
        self.height = 1.

        self.resizing_north = False
        self.resizing_east = False
        self.resizing_south = False
        self.resizing_west = False
        self.last_pos = None

        self.selected_scene = None

        self.parent = parent
        self.north_resize_area = wx.Window(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(-1, 2))
        self.east_resize_area = wx.Window(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(2, -1))
        self.south_resize_area = wx.Window(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(-1, 2))
        self.west_resize_area = wx.Window(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(2, -1))

        self.north_resize_area.SetCursor(wx.Cursor(wx.CURSOR_SIZENS))
        self.east_resize_area.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))
        self.south_resize_area.SetCursor(wx.Cursor(wx.CURSOR_SIZENS))
        self.west_resize_area.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))

        self.scene_choice = wx.Choice(self, wx.ID_ANY)
        self.scene_choice.SetToolTip('Select a scene to view')

        self.legend_button = wx.BitmapButton(self, wx.ID_ANY, get_resource_bitmap('stripes.png'))
        self.geodata_button = wx.BitmapButton(self, wx.ID_ANY, get_resource_bitmap('globe.png'))

        self.legend_button.SetToolTip('Show/hide legend')
        self.geodata_button.SetToolTip('Show place names')

        self.camera = object()  # Todo: Camera()
        self.gl_canvas = wx.Panel(self, wx.ID_ANY)  # Todo
        self.gl_canvas.SetBackgroundColour(wx.Colour(0, 0, 0))

        self.gl_canvas.Refresh()

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(self.scene_choice, 1, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        top_sizer.Add(self.legend_button, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 3)
        top_sizer.Add(self.geodata_button, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 3)

        content_sizer = wx.BoxSizer(wx.VERTICAL)
        content_sizer.Add(top_sizer, 0, wx.EXPAND | wx.ALL, 5)
        content_sizer.Add(self.gl_canvas, 1, wx.EXPAND)

        center_sizer = wx.BoxSizer(wx.HORIZONTAL)
        center_sizer.Add(self.west_resize_area, 0, wx.EXPAND)
        center_sizer.Add(content_sizer, 1, wx.EXPAND)
        center_sizer.Add(self.east_resize_area, 0, wx.EXPAND)

        sizer.Add(self.north_resize_area, 0, wx.EXPAND)
        sizer.Add(center_sizer, 1, wx.EXPAND)
        sizer.Add(self.south_resize_area, 0, wx.EXPAND)

        # Event handlers
        self.scene_choice.Bind(wx.EVT_CHOICE, self.on_scene_choice)
        self.legend_button.Bind(wx.EVT_BUTTON, self.on_legend_label)
        self.geodata_button.Bind(wx.EVT_BUTTON, self.on_geographic_label)

        self.north_resize_area.Bind(wx.EVT_LEFT_DOWN, self.on_resize_left_down)
        self.north_resize_area.Bind(wx.EVT_LEFT_UP, self.on_resize_left_up)
        self.north_resize_area.Bind(wx.EVT_MOTION, self.on_resize_motion)

        self.east_resize_area.Bind(wx.EVT_LEFT_DOWN, self.on_resize_left_down)
        self.east_resize_area.Bind(wx.EVT_LEFT_UP, self.on_resize_left_up)
        self.east_resize_area.Bind(wx.EVT_MOTION, self.on_resize_motion)

        self.south_resize_area.Bind(wx.EVT_LEFT_DOWN, self.on_resize_left_down)
        self.south_resize_area.Bind(wx.EVT_LEFT_UP, self.on_resize_left_up)
        self.south_resize_area.Bind(wx.EVT_MOTION, self.on_resize_motion)

        self.west_resize_area.Bind(wx.EVT_LEFT_DOWN, self.on_resize_left_down)
        self.west_resize_area.Bind(wx.EVT_LEFT_UP, self.on_resize_left_up)
        self.west_resize_area.Bind(wx.EVT_MOTION, self.on_resize_motion)

        self.gl_canvas.Bind(wx.EVT_LEFT_DCLICK, self.on_canvas_dclick)
        self.gl_canvas.Bind(wx.EVT_RIGHT_DOWN, self.on_canvas_right_click)

        # Todo: VI_EVENT_VIZPLUGIN_HAS_NEW_LEGEND event

        # self.gl_canvas.camera.set_wireframe(False)  # Todo

        self.gl_canvas.SetFocus()

        self.legend_window = object()  # Todo: LegendWindow()

        self.refresh_scenes()

        # Todo: observable

    def __del__(self):
        pass  # Todo

    def set_neighbor(self, neighbor, direction):
        if direction == self.NORTH:
            self.north_resize_area.Show()
            self.north.append(neighbor)

        elif direction == self.EAST:
            self.east_resize_area.Show()
            self.east = neighbor

        elif direction == self.SOUTH:
            self.south_resize_area.Show()
            self.south.append(neighbor)

        elif direction == self.WEST:
            self.west_resize_area.Show()
            self.west = neighbor

    def get_neighbor(self, direction):
        if direction == self.NORTH:
            return self.north[0] if self.north else None

        elif direction == self.EAST:
            return self.east

        elif direction == self.SOUTH:
            return self.south[0] if self.south else None

        elif direction == self.WEST:
            return self.west

    def remove_neighbor(self, neighbor):
        self.north.remove(neighbor)

        if self.east == neighbor:
            self.east = None

        self.south.remove(neighbor)

        if self.west == neighbor:
            self.west = None

    def reset_neighbors(self):
        self.north = []
        self.east = None
        self.south = []
        self.west = None

    def hide_resize_areas(self):
        self.north_resize_area.Hide()
        self.east_resize_area.Hide()
        self.south_resize_area.Hide()
        self.west_resize_area.Hide()

    def get_scene_choice(self):
        return self.scene_choice.GetSelection()

    def set_scene_choice(self, choice):
        self.scene_choice.SetSelection(choice)
        self.update_scene()

    def update_scene(self):
        pass  # Todo

    def on_resize_left_down(self, event):
        self.resizing_north = self.resizing_east = self.resizing_south = self.resizing_west = False

        if event.GetEventObject() == self.north_resize_area:
            self.resizing_north = True
            self.last_pos = event.y

            self.north_resize_area.CaptureMouse()

        elif event.GetEventObject() == self.east_resize_area:
            self.resizing_east = True
            self.last_pos = event.x

            self.east_resize_area.CaptureMouse()

        elif event.GetEventObject() == self.south_resize_area:
            self.resizing_south = True
            self.last_pos = event.y

            self.south_resize_area.CaptureMouse()

        elif event.GetEventObject() == self.west_resize_area:
            self.resizing_west = True
            self.last_pos = event.x

            self.west_resize_area.CaptureMouse()

    def on_resize_left_up(self, event):
        self.resizing_north = self.resizing_east = self.resizing_south = self.resizing_west = False

        if self.north_resize_area.HasCapture():
            self.north_resize_area.ReleaseMouse()
        if self.east_resize_area.HasCapture():
            self.east_resize_area.ReleaseMouse()
        if self.south_resize_area.HasCapture():
            self.south_resize_area.ReleaseMouse()
        if self.west_resize_area.HasCapture():
            self.west_resize_area.ReleaseMouse()

    def on_resize_motion(self, event):
        if self.resizing_north:
            diff = self.last_pos - event.y
            parent_height = self.GetParent().GetSize().GetHeight()
            prop_diff = diff / parent_height

            self.height += prop_diff

            # Update neighbors to the east
            east = self.east
            while east is not None:
                east.height += prop_diff
                east = east.east

            # Update neighbors to the west
            west = self.west
            while west is not None:
                west.height += prop_diff
                west = west.west

            for viewer in self.north:
                viewer.height -= prop_diff

        elif self.resizing_east:
            diff = event.x - self.last_pos
            parent_width = self.GetParent().GetSize().GetWidth()
            prop_diff = diff / parent_width

            self.width += prop_diff
            self.east.width -= prop_diff

        elif self.resizing_south:
            diff = event.y - self.last_pos
            parent_height = self.GetParent().GetSize().GetHeight()
            prop_diff = diff / parent_height

            self.height += prop_diff

            # Update neighbors to the east
            east = self.east
            while east is not None:
                east.height += prop_diff
                east = east.east

            # Update neighbors to the west
            west = self.west
            while west is not None:
                west.height += prop_diff
                west = west.west

            for viewer in self.south:
                viewer.height -= prop_diff

        elif self.resizing_west:
            diff = self.last_pos - event.x
            parent_width = self.GetParent().GetSize().GetWidth()
            prop_diff = diff / parent_width

            self.width += prop_diff
            self.west.width -= prop_diff

        self.GetParent().update_viewer_sizes()

    def on_canvas_dclick(self, event):
        pass  # Todo

    def on_canvas_right_click(self, event):
        pass  # Todo

    def on_canvas_popup_menu(self, event):
        pass  # Todo

    def refresh_scenes(self):
        pass  # Todo

    def fetch_scene_names(self, root):
        pass  # Todo

    def project_changed(self, event):
        pass  # Todo

    def on_scene_choice(self, event):
        self.update_scene()

    def on_legend_label(self, event):
        pass  # Todo

    def on_geographic_label(self, event):
        pass  # Todo

    def on_viz_has_new_legend(self, event):
        pass  # Todo

    def update_legend(self):
        pass  # Todo

    def reset_camera_interactor(self):
        pass  # Todo

    def update(self):
        pass  # Todo

    def update_geocoder_info(self):
        pass  # Todo

