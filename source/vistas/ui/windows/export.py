from vistas.core.export import ExportItem
from vistas.core.utils import get_platform

import wx
import wx.lib.intctrl


class ExportItemBitmap(wx.EvtHandler):

    HIT_NONE = 0
    HIT_NW = 1
    HIT_N = 2
    HIT_NE = 3
    HIT_E = 4
    HIT_SE = 5
    HIT_S = 6
    HIT_SW = 7
    HIT_W = 8

    ITEM_MIN_SIZE = 20

    def __init__(self, canvas, item: ExportItem):
        super().__init__()
        self.canvas = canvas
        self.item = item
        self.offset = wx.DefaultPosition
        self.selected = False
        self.moving = False
        self.sizing = False

        self.start_position = wx.DefaultPosition
        self.start_size = wx.DefaultSize
        self.sizing_handle = self.HIT_NONE

        self.RefreshCache()
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

    @property
    def position(self):
        paint_x, paint_y = self.canvas.paint_offset_x, self.canvas.paint_offset_y
        pos_x, pos_y = self.item.position
        return wx.Position(pos_x - paint_x, pos_y - paint_y)

    @property
    def size(self):
        return wx.Size(*self.item.size)

    def HitTest(self, point):
        size = self.size

        if point.x <= 3:
            if point.y <= 3:
                return self.HIT_NW
            elif size.y / 2 - 3 <= point.y <= size.y / 2 + 3:
                return self.HIT_W
            elif point.y >= size.y - 3:
                return self.HIT_SW
        elif point.x >= size.x - 3:
            if point.y <= 3:
                return self.HIT_NW
            elif size.y / 2 - 3 <= point.y <= size.y / 2 + 3:
                return self.HIT_W
            elif point.y >= size.y - 3:
                return self.HIT_SW
        elif point.y <= 3 and size.x / 2 - 3 <= point.x <= point.x / 2 + 3:
            return self.HIT_N
        elif point.y >= size.y - 3 and size.x / 2 - 3 <= point.x <= point.x / 2 + 3:
            return self.HIT_S
        return self.HIT_NONE

    def Select(self):
        self.selected = True

    def Deselect(self):
        self.selected = False

    def IsSelected(self):
        return self.selected

    def Draw(self, dc: wx.AutoBufferedPaintDC):
        pass    # Todo

    def RefreshCache(self, force=False):
        if self.item.item_type in [ExportItem.SCENE, ExportItem.FIGURE]:
            self.cache = self.item.snapshot(force)  # Get as wx.Bitmap
        else:
            self.cache = self.item.snapshot(force)  # Get as wx.Bitmap (true) <-- true for getting transparency

    def OnMotion(self, event):
        paint_offset_x = self.canvas.paint_offset_x
        paint_offset_y = self.canvas.paint_offset_y
        event_pos = event.GetPosition()

        if self.selected and self.moving:
            position = self.position
            self.item.position = (
                position.x + event_pos.x - self.offset.x + paint_offset_x,
                position.y + event_pos.y - self.offset.y + paint_offset_y
            )
            self.canvas.Refresh()
        elif self.selected and self.sizing:
            rect = wx.Rect(self.start_position, self.start_size)
            new_size = False
            new_position = False
            diff_x, diff_y = event_pos.x - self.offset.x, event_pos.y - self.offset.y

            if wx.GetKeyState(wx.WXK_SHIFT):    # Even box sizing
                if abs(diff_x / self.start_size.x) > abs(diff_y / self.start_size.y):
                    diff_y = self.start_size.y * diff_x / self.start_size.x
                elif abs(diff_y / self.start_size.y) > abs(diff_x / self.start_size.x):
                    diff_x = self.start_size.x * diff_y / self.start_size.y

            if self.sizing_handle in [self.HIT_NW, self.HIT_N, self.HIT_NE]:
                rect.y += diff_y
                rect.height -= diff_y
                self.offset.y = -diff_y
                new_size = True
                new_position = True

            if self.sizing_handle in [self.HIT_NW, self.HIT_W, self.HIT_SW]:
                rect.x += diff_x
                rect.width -= diff_x
                self.offset.y = -diff_x
                new_size = True
                new_position = True

            if self.sizing_handle in [self.HIT_SW, self.HIT_S, self.HIT_SE]:
                rect.height += diff_y
                new_size = True

            if self.sizing_handle in [self.HIT_NE, self.HIT_E, self.HIT_SE]:
                rect.width += diff_x
                new_size = True

            if new_size:
                adjust_x = max(rect.width, self.ITEM_MIN_SIZE) - rect.width
                adjust_y = max(rect.height, self.ITEM_MIN_SIZE) - rect.height
                rect.width += adjust_x
                rect.height += adjust_y
                rect.x -= adjust_x
                rect.y -= adjust_y

                self.item.size = (rect.width, rect.height)

            if new_position:
                self.item.position = (rect.x, rect.y)

            self.canvas.Refresh()

        elif self.selected:
            hit = self.HitTest(event.GetPosition())

            if hit is self.HIT_NONE:
                cursor = wx.Cursor(wx.CURSOR_ARROW)
            elif hit in [self.HIT_NW, self.HIT_SE]:
                cursor = wx.Cursor(wx.CURSOR_SIZENWSE)
            elif hit in [self.HIT_N, self.HIT_S]:
                cursor = wx.Cursor(wx.CURSOR_SIZENS)
            elif hit in [self.HIT_NE, self.HIT_SW]:
                cursor = wx.Cursor(wx.CURSOR_SIZENESW)
            elif hit in [self.HIT_E, self.HIT_W]:
                cursor = wx.Cursor(wx.CURSOR_SIZEWE)
            else:
                raise ValueError("Hit Test returned an invalid handle!")
            self.canvas.SetCursor(cursor)

        event.Skip()

    def OnLeftDown(self, event):
        if self.selected:
            hit = self.HitTest(event.GetPosition())
            self.canvas.CaptureItem(self)
            self.offset = event.GetPosition()
            if hit is self.HIT_NONE:
                self.moving = True
            else:
                position = self.position
                self.canvas.CaptureItem(self)
                self.sizing = True
                self.offset = event.GetPosition()
                self.start_position = (position.x + self.canvas.paint_offset_x, position.y + self.canvas.paint_offset_y)
                self.start_size = self.size
                self.sizing_handle = self.HitTest(event.GetPosition())

        event.Skip()

    def OnLeftUp(self, event):
        self.canvas.ReleaseItem()
        self.sizing = False
        self.moving = False
        event.Skip()


class ExportCanvas(wx.ScrolledWindow):

    def __init__(self, parent, id):
        super().__init__(parent, id, style=wx.HSCROLL | wx.VSCROLL)
        self.captured_item = None
        self.selected_item = None
        self.items = []

        self.scroll_x, self.scroll_y = 0, 0

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        if get_platform() == 'windows':
            self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_SCROLLWIN_TOP, self.OnScroll)
        self.Bind(wx.EVT_SCROLLWIN_BOTTOM, self.OnScroll)
        self.Bind(wx.EVT_SCROLLWIN_THUMBTRACK, self.OnScroll)
        self.Bind(wx.EVT_SCROLLWIN_THUMBRELEASE, self.OnScroll)

    def __del__(self):
        pass

    def HitTest(self, point):
        for item in reversed(self.items):
            if item.Hit(point):
                return item

    def ConnectEvents(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_MOTION, self.OnMouse)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMouse)
        self.Bind(wx.EVT_LEFT_UP, self.OnMouse)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnMouse)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnMouse)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnCaptureLost)

    def AddItem(self, item: ExportItem) -> ExportItemBitmap:
        canvas_item = ExportItemBitmap(self, item)
        self.items.append(canvas_item)
        self.Refresh()
        return canvas_item

    def DeleteItem(self, item: ExportItemBitmap):
        if item in self.items:
            if item is self.captured_item:
                self.ReleaseItem()
            if item is self.selected_item:
                self.DeselectItem()
            self.items.remove(item)
            self.Refresh()

    def DeleteAllItems(self):
        self.items = []
        self.Refresh()

    def CaptureItem(self, item: ExportItemBitmap):
        self.CaptureMouse()
        self.captured_item = item

    def ReleaseItem(self):
        if self.HasCapture():
            self.ReleaseMouse()
        self.captured_item = None

    def SelectItem(self, item: ExportItemBitmap):
        if self.selected_item is not None:
            self.selected_item.Deselect()
        self.selected_item = item
        self.selected_item.Select()

    def DeselectItem(self):
        if self.selected_item is not None:
            self.selected_item.Deselect()
            self.selected_item = None
            self.Refresh()

    def RefreshItemCache(self, item: ExportItem):
        for export_item in self.items:
            if export_item.item is item:
                export_item.RefreshCache()
                break

    def SendToFront(self, item: ExportItemBitmap):
        for export_item in self.items:
            if export_item is item:
                self.items.remove(item)
        self.items.append(item)
        self.Refresh()

    def SendToBack(self, item: ExportItemBitmap):
        for export_item in self.items:
            if export_item is item:
                self.items.remove(item)
        self.items.insert(0, item)
        self.Refresh()

    def OnEraseBackground(self, event):
        pass

    def OnSize(self, event: wx.SizeEvent):
        size = event.GetSize()
        max_size = self.GetMaxSize()
        if size.x == max_size.x:
            self.SetScrollbar(wx.HORIZONTAL, 0, 0, 0)
            self.scroll_y = 0
        else:
            self.scroll_x = self.GetScrollPos(wx.HORIZONTAL)
        if size.y == max_size.y:
            self.SetScrollbar(wx.VERTICAL, 0, 0, 0)
            self.scroll_y = 0
        else:
            self.scroll_y = self.GetScrollPos(wx.VERTICAL)

    def OnScroll(self, event: wx.ScrollEvent):
        self.scroll_x = self.GetScrollPos(wx.HORIZONTAL)
        self.scroll_y = self.GetScrollPos(wx.VERTICAL)
        self.Refresh()
        event.Skip()

    def OnPaint(self, event: wx.PaintEvent):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.BLACK_BRUSH)
        dc.Clear()

        position = wx.DefaultPosition
        size = wx.DefaultSize

        for export_item in self.items:
            export_item.Draw(dc)
            if export_item == self.selected_item:
                position = self.selected_item.GetPosition()
                size = self.selected_item.GetSize()

        if position != wx.DefaultPosition and size != wx.DefaultSize:
            dc.SetBrush(wx.WHITE_BRUSH)
            dc.SetPen(wx.WHITE_PEN)

            dc.DrawLine(position.x, position.y, position.x + size.x, position.y)
            dc.DrawLine(position.x + size.x, position.y - 3, position.x + size.x, position.y + size.y - 3)
            dc.DrawLine(position.x + size.x - 3, position.y + size.y, position.x - 3, position.y + size.y)
            dc.DrawLine(position.x, position.y + size.y - 3, position.x + size.x, position.y - 3)

            # NW
            dc.DrawRectangle(position.x - 3, position.y - 3, 6, 6)

            # N
            dc.DrawRectangle(position.x + size.x / 2 - 3, position.y - 3, 6, 6)

            # NE
            dc.DrawRectangle(position.x + size.x - 3, position.y - 3, 6, 6)

            # E
            dc.DrawRectangle(position.x + size.x - 3, position.y + size.y / 2 - 3, 6, 6)

            # SE
            dc.DrawRectangle(position.x + size.x - 3, position.y + size.y - 3, 6, 6)

            # S
            dc.DrawRectangle(position.x + size.x / 2 - 3, position.y + size.y - 3, 6, 6)

            # SW
            dc.DrawRectangle(position.x - 3, position.y + size.y - 3, 6, 6)

            # W
            dc.DrawRectangle(position.x - 3, position.y + size.y / 2 - 3, 6, 6)

    def OnMouse(self, event: wx.MouseEvent):
        if self.HasCapture() and self.captured_item is not None:
            hit_item = self.captured_item
        else:
            hit_item = self.HitTest(event.GetPosition())

        if hit_item is not None:
            event.SetX(event.GetX() - hit_item.position.x)
            event.SetY(event.GetY() - hit_item.position.y)
            event.SetEventObject(hit_item)

            wx.PostEvent(hit_item, event)
            event.Skip(False)
        else:
            self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
            event.Skip(True)

    def OnCaptureLost(self, event):
        self.captured_item = None


class ExportFrame(wx.Frame):

    def __init__(self, parent, id):
        super().__init__(parent, id, "Export Animation", style=wx.DEFAULT_FRAME_STYLE)

        main_panel = wx.Panel(self, wx.ID_ANY)
        width_static = wx.StaticText(main_panel, wx.ID_ANY, "Width:")
        self.width_text = wx.lib.intctrl.IntCtrl(main_panel, wx.ID_ANY, value=600)
        height_static = wx.StaticText(main_panel, wx.ID_ANY, "Height:")
        self.height_text = wx.TextCtrl(main_panel, wx.ID_ANY, value=800)
        self.canvas = ExportCanvas(main_panel, wx.ID_ANY)
        self.fit_frame_button = wx.Button(main_panel, wx.ID_ANY, "Fit Window")
        self.fit_frame_button.SetToolTip("Fits exporter width and height to the size of items in the window")
        self.export_button = wx.Button(main_panel, wx.ID_ANY, "Export")
        self.export_button.SetDefault()

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)

        main_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        main_panel.SetSizer(main_panel_sizer)

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(width_static, 0, wx.RIGHT, 5)
        top_sizer.Add(self.width_text, 0, wx.RIGHT, 10)
        top_sizer.Add(height_static, 0, wx.RIGHT, 5)
        top_sizer.Add(self.height_text)

        main_panel_sizer.Add(top_sizer, 0, wx.EXPAND | wx.ALL, 10)
        main_panel_sizer.Add(self.canvas, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.fit_frame_button)
        button_sizer.AddStretchSpacer(1)
        button_sizer.Add(self.export_button)

        main_panel_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        main_sizer.Add(main_panel, 1, wx.EXPAND)
        self.Bind(wx.EVT_MAXIMIZE, self.OnMaximize)

    def SetCanvasSize(self, width, height):
        self.SetMaxSize(wx.Size(-1, -1))
        size = wx.Size(width, height)
        self.canvas.SetMinSize(size)
        self.canvas.SetMaxSize(size)
        self.width_text.SetValue("{}".format(width))
        self.height_text.SetValue("{}".format(height))
        self.canvas.SetClientSize(size)
        self.canvas.SetScrollRate(1, 1)
        self.canvas.SetVirtualSize(size)
        self.Fit()
        self.SetMaxSize(self.GetSize())

    def OnMaximize(self, event):
        self.Restore()
        self.Fit()
        wx.PostEvent(self.canvas, wx.SizeEvent(self.GetSize()))
