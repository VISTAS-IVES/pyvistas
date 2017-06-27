from vistas.core.export import Exporter, ExportItem
from vistas.core.plugins.visualization import VisualizationPlugin2D, VisualizationPlugin3D
from vistas.core.timeline import Timeline
from vistas.core.graphics.camera import Camera
from vistas.core.graphics.camera_interactor import SphereInteractor
from vistas.ui.project import Project
from vistas.ui.windows.export import ExportFrame, ExportItemBitmap
from vistas.ui.windows.export_scene_dialog import ExportSceneDialog

import wx


class ExportTextCtrl(wx.TextCtrl):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item = None


class ExportDeleteTimer(wx.Timer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item_to_delete = None


class ExportController(wx.EvtHandler):

    MENU_ADD_LABEL = 0
    MENU_ADD_TIMESTAMP = 1
    MENU_ADD_SCENE = 2
    MENU_CHANGE_FONT_SIZE = 3
    MENU_SET_FLYTHROUGH = 4
    MENU_ADD_VIZ = 5
    MENU_ADD_LEGEND = 6
    MENU_NO_SCENES = 7
    MENU_NO_LEGENDS = 8
    MENU_NO_FLYTHROUGHS = 9
    MENU_SET_NO_FLYTHROUGH = 10
    MENU_NO_VIZ = 11
    MENU_DELETE_ITEM = 12
    MENU_SEND_TO_BACK = 13
    MENU_BRING_TO_FRONT = 14
    MENU_EDIT_CAMERA_POS = 15
    MENU_FONT_SIZE = 50
    MENU_ADD_PROJECT_ITEM = 100
    MENU_ADD_SCENE_LEGEND = 200

    def __init__(self):
        super().__init__()
        self.export_frame = ExportFrame(None, wx.ID_ANY)
        self.project = Project.get()
        self.frame_position = wx.DefaultPosition
        self.canvas_size = None
        self.export_frame.Hide()
        self.export_frame.SetCanvasSize(*self.project.exporter.size)

        self.export_frame.Bind(wx.EVT_CLOSE, self.OnFrameClose)
        self.export_frame.width_text.Bind(wx.EVT_TEXT, self.OnSizeTextChange)
        self.export_frame.height_text.Bind(wx.EVT_TEXT, self.OnSizeTextChange)
        self.export_frame.fit_frame_button.Bind(wx.EVT_BUTTON, self.OnFitFrameButton)
        self.export_frame.export_button.Bind(wx.EVT_BUTTON, self.OnExportButton)
        self.export_frame.canvas.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.export_frame.canvas.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.export_frame.canvas.ConnectEvents()

        self.mouse_pos = wx.DefaultPosition
        self.popup_nodes = {}

    def __del__(self):
        self.export_frame.Destroy()

    def Reset(self):
        self.export_frame.canvas.DeleteAllItems()

    def ShowWindow(self):
        self.export_frame.SetPosition(self.frame_position)
        self.export_frame.Show()
        self.export_frame.Raise()

    def SetExportWindow(self, exporter: Exporter):
        self.Reset()
        if self.project.exporter.items:
            for item in exporter.items:
                self.project.exporter.add_item(item)
            size = exporter.size
            self.project.exporter.size = size
            self.export_frame.SetCanvasSize(*size)
            self.canvas_size = size
        else:
            size = self.project.exporter.size

            if self.canvas_size is None:
                self.canvas_size = size
            elif not (self.canvas_size == size):
                size = self.canvas_size
            self.project.exporter.size = size
            self.export_frame.SetCanvasSize(*size)

        for item in self.project.exporter.items:
            canvas_item = self.export_frame.canvas.AddItem(item)
            canvas_item.Bind(wx.EVT_LEFT_DOWN, self.OnItemLeftDown)
            canvas_item.Bind(wx.EVT_LEFT_DCLICK, self.OnItemDClick)
            canvas_item.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)

    def SaveState(self, state):
        pass    # Todo - implement

    def LoadState(self, state):
        pass    # Todo - implement

    def OnFrameClose(self, event):
        self.frame_position = self.export_frame.GetPosition()
        self.canvas_size = self.export_frame.width_text.GetValue(), self.export_frame.height_text.GetValue()
        self.export_frame.canvas.DeselectItem()
        self.export_frame.Hide()
        event.Skip(False)

    def OnSizeTextChange(self, event):
        size = self.export_frame.width_text.GetValue(), self.export_frame.height_text.GetValue()
        self.project.exporter.size = size
        self.export_frame.SetCanvasSize(*size)

    def OnFitFrameButton(self, event):
        self.project.exporter.fit_to_items()
        self.export_frame.SetCanvasSize(*self.project.exporter.size)
        self.export_frame.Refresh()

    def OnExportButton(self, event):
        pass    # Todo - implement

    def OnLeftDown(self, event):
        focus_win = wx.Window.FindFocus()
        if focus_win is not None:
            evt = wx.FocusEvent()
            evt.SetEventObject(focus_win)
            wx.PostEvent(focus_win, evt)

        self.export_frame.canvas.SetFocus()
        self.export_frame.canvas.DeselectItem()
        event.Skip()

    def OnRightDown(self, event):
        popup_menu = wx.Menu()
        scenes_menu = wx.Menu()
        legends_menu = wx.Menu()
        viz_menu = wx.Menu()
        fly_menu = wx.Menu()
        font_menu = wx.Menu()

        self.popup_nodes = {}

        popup_menu.Append(self.MENU_ADD_LABEL, "Add Label")
        popup_menu.Append(self.MENU_ADD_TIMESTAMP, "Add Timestamp")

        scenes = self.project.all_scenes
        index = 0
        if scenes:
            for scene_node in scenes:
                id = self.MENU_ADD_PROJECT_ITEM + index
                scenes_menu.Append(id, scene_node.scene.name)
                self.popup_nodes[id] = scene_node
                legends_menu.Append(self.MENU_ADD_SCENE_LEGEND + index, scene_node.label)
                index += 1
        else:
            scenes_menu.Append(self.MENU_NO_SCENES, "No scenes available")
            scenes_menu.Enable(self.MENU_NO_SCENES, False)
            legends_menu.Append(self.MENU_NO_LEGENDS, "No legends available")
            legends_menu.Enable(self.MENU_NO_LEGENDS, False)

        visualizations = [v for v in self.project.all_visualizations
                          if isinstance(v.visualization, VisualizationPlugin2D)]
        if visualizations:
            for viz_node in visualizations:
                id = self.MENU_ADD_PROJECT_ITEM + index
                viz_menu.Append(id, viz_node.label)
                self.popup_nodes[id] = viz_node
                index += 1
        else:
            viz_menu.Append(self.MENU_NO_VIZ, "No visualizations available")
            viz_menu.Enable(self.MENU_NO_VIZ, False)

        popup_menu.AppendSubMenu(scenes_menu, "Add Scene")
        popup_menu.AppendSubMenu(viz_menu, "Add 2D Visualization")
        popup_menu.AppendSubMenu(legends_menu, "Add Legend")
        popup_menu.AppendSeparator()
        font_menu_item = popup_menu.AppendSubMenu(font_menu, "Set Font Size")
        fly_menu_item = popup_menu.AppendSubMenu(fly_menu, "Set Flythrough")
        popup_menu.AppendSeparator()
        popup_menu.Append(self.MENU_DELETE_ITEM, "Delete Item")
        popup_menu.AppendSeparator()
        popup_menu.Append(self.MENU_BRING_TO_FRONT, "Bring Item to front")
        popup_menu.Append(self.MENU_SEND_TO_BACK, "Send Item to back")
        popup_menu.Append(self.MENU_EDIT_CAMERA_POS, "Edit scene orientation")

        item = event.GetEventObject()

        if item is not None and isinstance(item, ExportItemBitmap) and item.item is not None:
            self.export_frame.canvas.SelectItem(item)

            # If the item is not a label or timestamp, don't enable font size controls
            item_type = item.item.item_type
            if item_type not in [ExportItem.LABEL, ExportItem.TIMESTAMP]:
                popup_menu.Enable(font_menu_item.GetId(), False)
            else:
                for i in range(8, 18, 2):
                    font_id = self.MENU_FONT_SIZE + i
                    font_menu.AppendCheckItem(font_id, str(i))
                    if item.item.font_size == i:
                        font_menu.Check(font_id, True)

            # If there is only one item, disable to front/back controls
            if len(self.project.exporter.items) <= 1:
                popup_menu.Enable(self.MENU_BRING_TO_FRONT, False)
                popup_menu.Enable(self.MENU_SEND_TO_BACK, False)

            # If the item is not a scene, disable flythrough controls
            if item_type is not ExportItem.SCENE:
                popup_menu.Enable(self.MENU_EDIT_CAMERA_POS, False)
                popup_menu.Enable(fly_menu_item.GetId(), False)

            # Otherwise, check the selected item's children for flythroughs to add
            else:
                selected_item = self.export_frame.canvas.selected_item
                project_node = self.project.get_node_by_id(selected_item.item.project_node_id)
                flythroughs = project_node.flythrough_nodes
                if flythroughs:
                    fly_menu.AppendCheckItem(self.MENU_SET_NO_FLYTHROUGH, "No Flythrough")
                    flythrough_set = False
                    for fly_node in flythroughs:
                        id = self.MENU_ADD_PROJECT_ITEM + index
                        fly_menu.AppendCheckItem(id, fly_node.label)
                        self.popup_nodes[id] = fly_node

                        # Check the item if the flythrough in the fly node is the same as the flythrough in the item
                        if selected_item.item.flythrough is fly_node.flythrough:
                            fly_menu.Check(id, True)
                            flythrough_set = True

                        index += 1

                    if flythrough_set:
                        popup_menu.Enable(self.MENU_EDIT_CAMERA_POS, False)
                    else:
                        fly_menu.Check(self.MENU_SET_NO_FLYTHROUGH, True)

                # If there are no flythroughs, disable the flythrough menu
                else:
                    fly_menu.Append(self.MENU_NO_FLYTHROUGHS, "No flythroughs available")
                    fly_menu.Enable(self.MENU_NO_FLYTHROUGHS, False)

        else:
            popup_menu.Enable(self.MENU_DELETE_ITEM, False)
            popup_menu.Enable(self.MENU_BRING_TO_FRONT, False)
            popup_menu.Enable(self.MENU_SEND_TO_BACK, False)
            popup_menu.Enable(self.MENU_EDIT_CAMERA_POS, False)
            popup_menu.Enable(font_menu_item.GetId(), False)
            popup_menu.Enable(fly_menu_item.GetId(), False)

        popup_menu.Bind(wx.EVT_MENU, self.OnPopupMenu)
        self.mouse_pos = event.GetPosition()
        self.export_frame.canvas.PopupMenu(popup_menu)

    def OnPopupMenu(self, event):
        item = ExportItem()

        offset_x = self.export_frame.canvas.scroll_x
        offset_y = self.export_frame.canvas.scroll_y
        item.position = (self.mouse_pos.x + offset_x, self.mouse_pos.y + offset_y)

        id = event.GetId()

        if id == self.MENU_ADD_LABEL:
            item.item_type = ExportItem.LABEL
            item.size = (100, 100)
            item.label = "New Label"

        elif id == self.MENU_ADD_TIMESTAMP:
            item.item_type = ExportItem.TIMESTAMP
            item.time_format = Timeline.app().time_format

        elif id == self.MENU_DELETE_ITEM:
            item_to_delete = self.export_frame.canvas.selected_item
            self.project.exporter.remove_item(item_to_delete.item)
            self.export_frame.canvas.DeleteItem(item_to_delete)
            return

        elif id == self.MENU_BRING_TO_FRONT:
            item_to_front = self.export_frame.canvas.selected_item
            self.project.exporter.send_to_front(item_to_front.item)
            self.export_frame.canvas.SendToFront(item_to_front)
            self.export_frame.canvas.SelectItem(item_to_front)
            return

        elif id == self.MENU_SEND_TO_BACK:
            item_to_back = self.export_frame.canvas.selected_item
            self.project.exporter.send_to_back(item_to_back.item)
            self.export_frame.canvas.SendToBack(item_to_back)
            self.export_frame.canvas.SelectItem(item_to_back)
            return

        elif id == self.MENU_EDIT_CAMERA_POS:
            self.CreateExportSceneDialog(self.export_frame.canvas.selected_item.item)
            return

        elif id == self.MENU_SET_NO_FLYTHROUGH:
            item = self.export_frame.canvas.selected_item.item
            item.flythrough = None
            return

        elif id >= self.MENU_ADD_SCENE_LEGEND:
            project_node = self.popup_nodes[id - self.MENU_ADD_SCENE_LEGEND]
            if project_node.is_scene:
                item.item_type = ExportItem.LEGEND
                item.size = (200, 400)
                visualizations = self.project.find_viz_with_parent_scene(project_node.scene)
                for viz in visualizations:
                    if isinstance(viz, VisualizationPlugin3D):
                        item.viz_plugin = viz
                        break
                item.project_node_id = project_node.node_id

        elif id >= self.MENU_ADD_PROJECT_ITEM:
            project_node = self.popup_nodes[id - self.MENU_ADD_PROJECT_ITEM]
            if project_node.is_scene:
                item.item_type = ExportItem.SCENE
                item.size = (400, 400)
                item.project_node_id = project_node.node_id
                camera = Camera(project_node.scene)
                camera_interactor = SphereInteractor(camera)    # Only needed to set the viewport properly
                item.camera = camera

                fly_nodes = project_node.flythrough_nodes
                if fly_nodes:
                    item.flythrough = fly_nodes[0]  # If available, set first flythrough by default
                    item.flythrough_node_id = fly_nodes[0].node_id

            elif project_node.is_visualization:
                item.item_type = ExportItem.VISUALIZATION
                item.size = (200, 200)
                item.viz_plugin = project_node.visualization
                item.project_node_id = project_node.node_id

            elif project_node.is_flythrough:
                item = self.export_frame.canvas.selected_item.item
                item.flythrough = project_node.flythrough
                item.flythrough_node_id = project_node.node_id
                return

        elif id >= self.MENU_FONT_SIZE:
            font_size = id - self.MENU_FONT_SIZE
            item = self.export_frame.canvas.selected_item.item
            item.font_size = font_size
            self.export_frame.canvas.RefreshItemCache(item)
            self.export_frame.Refresh()
            return
        else:
            print("Unknown popup ID: {}".format(id))
            return

        self.project.exporter.add_item(item)
        canvas_item = self.export_frame.canvas.AddItem(item)
        self.export_frame.canvas.SelectItem(canvas_item)
        canvas_item.Bind(wx.EVT_LEFT_DOWN, self.OnItemLeftDown)
        canvas_item.Bind(wx.EVT_LEFT_DCLICK, self.OnItemDClick)
        canvas_item.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)

    def OnItemLeftDown(self, event):
        self.export_frame.canvas.SelectItem(event.GetEventObject())
        event.Skip(True)

    def OnItemDClick(self, event):
        canvas_item = event.GetEventObject()
        item = canvas_item.item
        rect = canvas_item.rect
        item_type = item.item_type

        # Edit the label or timestamp text
        if item_type in [ExportItem.LABEL, ExportItem.TIMESTAMP]:
            text_ctrl = ExportTextCtrl(
                self.export_frame.canvas, wx.ID_ANY, item.label, pos=rect.GetPosition(),
                size=wx.Size(rect.width + 20, rect.height + 20),
                style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER | wx.TE_NO_VSCROLL
            )

            if item_type == ExportItem.TIMESTAMP:
                text_ctrl.SetValue(item.time_format)

            text_ctrl.SetFont(wx.Font(wx.FontInfo(item.font_size)))

            text_ctrl.SetFocus()
            text_ctrl.SetSelection(-1, -1)
            text_ctrl.Bind(wx.EVT_TEXT, self.OnTextUpdate)
            text_ctrl.Bind(wx.EVT_KILL_FOCUS, self.OnTextEndInput)
            text_ctrl.Bind(wx.EVT_TEXT_ENTER, self.OnTextEndInput)

            text_ctrl.item = canvas_item

        # Edit the scene in an interactive viewer
        elif item_type in [ExportItem.SCENE]:
            self.CreateExportSceneDialog(item)

    def CreateExportSceneDialog(self, item: ExportItem):
        config = ExportSceneDialog(self.export_frame.canvas, wx.ID_ANY, item)
        config.CenterOnParent()
        config.ShowModal()

    def CleanTextInput(self, string):
        pass    # Todo - is this needed anymore? Probably...

    def OnTextUpdate(self, event):
        text_ctrl = event.GetEventObject()
        old_size = text_ctrl.GetSize()
        longest_line = max(text_ctrl.GetValue().split('\n'), key=len)
        size = text_ctrl.GetFullTextExtent(longest_line)
        if old_size.x < size[0] + 25:
            old_size.x += 25
            text_ctrl.SetSize(old_size)
        event.Skip()

    def OnTextEndInput(self, event):
        text_ctrl = event.GetEventObject()
        canvas_item = text_ctrl.item
        mouse = wx.GetMouseState()

        if not mouse.ShiftDown():
            if not text_ctrl.IsShown():
                return

            input_text = text_ctrl.GetValue()

            if canvas_item.item.item_type is ExportItem.LABEL:
                canvas_item.item.label = input_text
            else:
                canvas_item.item.time_format = input_text
            canvas_item.RefreshCache()
            text_ctrl.Hide()

            timer = ExportDeleteTimer(self)
            timer.item_to_delete = text_ctrl
            timer.Bind(wx.EVT_TIMER, self.OnTextTimer)
            timer.Start(1, True)
            self.export_frame.canvas.Refresh()

        else:
            old_size = text_ctrl.GetSize()
            size = text_ctrl.GetFullTextExtent("0")
            old_size.y += size[1]
            text_ctrl.SetSize(old_size)

    def OnTextTimer(self, event):
        text_ctrl = event.GetEventObject().item_to_delete
        text_ctrl.Destroy()
