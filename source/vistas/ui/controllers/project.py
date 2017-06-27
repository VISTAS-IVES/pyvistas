import itertools
import logging
import os

import wx

from vistas.core.graphics.scene import Scene
from vistas.core.timeline import Timeline
from vistas.core.plugins.management import get_data_plugins, get_visualization_plugins, get_2d_visualization_plugins
from vistas.core.plugins.visualization import VisualizationPlugin3D
from vistas.core.graphics.flythrough import Flythrough
from vistas.ui.project import Project, SceneNode, FolderNode, VisualizationNode, DataNode, FlythroughNode
from vistas.ui.events import ProjectChangedEvent
from vistas.ui.windows.viz_dialog import VisualizationDialog
from vistas.ui.windows.flythrough_dialog import FlythroughDialog
from vistas.ui.windows.data_dialog import DataDialog, CalculateStatsThread
from vistas.ui.windows.task_dialog import TaskDialog

logger = logging.getLogger(__name__)


class ProjectTreeMenu(wx.Menu):
    def __init__(self, tree, item):
        super().__init__()

        self.item = item
        self.tree = tree


class ProjectController(wx.EvtHandler):
    POPUP_RENAME = 1
    POPUP_ADD_FOLDER = 2
    POPUP_ADD_DATA_FILE = 3
    POPUP_ADD_SCENE = 4
    POPUP_ADD_VISUALIZATION = 5
    POPUP_ADD_FLYTHROUGH = 6
    POPUP_DELETE = 7

    scene_count = 0
    flythrough_count = 0

    def __init__(self, project_panel):
        self.has_save_path = False
        self.project_panel = project_panel
        self.project = Project()
        self.project.make_current()
        self.save_path = None
        self.drag_item = None

        self.NewProject(False)

        data_tree = self.project_panel.data_tree
        visualization_tree = self.project_panel.visualization_tree

        for tree in (data_tree, visualization_tree):
            tree.Bind(wx.EVT_TREE_KEY_DOWN, self.OnTreeKeyDown)
            tree.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.OnTreeItemBeginEdit)
            tree.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.OnTreeItemEndEdit)
            tree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnTreeItemRightClick)
            tree.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnTreeBeginDrag)
            tree.Bind(wx.EVT_TREE_END_DRAG, self.OnTreeEndDrag)
            tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnTreeItemActivate)

        visualization_tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeItemSelected)

    def SetProjectName(self, set_main_window_title=True):
        if self.save_path is not None:
            self.project.name = os.path.splitext(os.path.split(self.save_path)[-1])[0]
        else:
            self.project.name = 'Untitled Project'

        if set_main_window_title:
            self.SetMainWindowTitle()

    def SetMainWindowTitle(self):
        main_window = wx.GetTopLevelParent(self.project_panel)
        main_window.SetTitle('{} - VISTAS'.format(self.project.name))

    def NewProject(self, prompt=True, default_scene=True):
        md = wx.MessageDialog(
            wx.GetTopLevelParent(self.project_panel),
            'Are you sure you wish to start a new project? Any unsaved changes will be lost.', 'New Project',
            wx.OK | wx.CANCEL
        )

        if not prompt or md.ShowModal() == wx.ID_OK:
            data_tree = self.project_panel.data_tree
            visualization_tree = self.project_panel.visualization_tree

            data_tree.DeleteChildren(data_tree.GetRootItem())
            visualization_tree.DeleteChildren(visualization_tree.GetRootItem())

            self.RecursiveDeleteNode(self.project.visualization_root, False)
            self.RecursiveDeleteNode(self.project.data_root, False)

            self.project = Project()
            self.project.make_current()

            self.save_path = None
            self.has_save_path = False
            ProjectController.scene_count = 0

            self.SetMainWindowTitle()

            if default_scene:
                default_scene_node = SceneNode(Scene('Default Scene'), 'Default Scene', self.project.visualization_root)
                tree_parent = self.project_panel.visualization_tree.GetRootItem()
                self.project_panel.visualization_tree.AppendSceneItem(
                    tree_parent, default_scene_node.label, default_scene_node
                )

            data_tree.SetItemData(data_tree.GetRootItem(), self.project.data_root)
            visualization_tree.SetItemData(
                visualization_tree.GetRootItem(), self.project.visualization_root
            )
            data_tree.SetItemHasChildren(data_tree.GetRootItem(), True)
            visualization_tree.SetItemHasChildren(visualization_tree.GetRootItem(), True)
            data_tree.Expand(data_tree.GetRootItem())
            visualization_tree.Expand(visualization_tree.GetRootItem())

            self.project_panel.notebook.SetSelection(0)
            self.RefreshTimeline()

            wx.PostEvent(
                wx.GetTopLevelParent(self.project_panel),
                ProjectChangedEvent(change=ProjectChangedEvent.PROJECT_RESET)
            )

    def SaveProject(self):
        if not self.has_save_path:
            return self.SaveProjectAs()

        self.project.save(self.save_path)
        self.SetProjectName()
        self.project.dirty = False

        return True

    def SaveProjectAs(self):
        fd = wx.FileDialog(
            wx.GetTopLevelParent(self.project_panel), 'Choose a file', wildcard='*.vistas',
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )

        if fd.ShowModal() == wx.ID_OK:
            self.save_path = fd.GetPath()
            self.has_save_path = True

            return self.SaveProject()

        return False

    def LoadProject(self, path):
        if os.path.isfile(path):
            try:
                self.NewProject(False, False)
                self.save_path = path
                self.has_save_path = True
                self.project.load(path)
                self.PopulateTreesFromProject(self.project)
                self.SetProjectName()
            except:
                logger.exception('Error loading project')

                md = wx.MessageDialog(None, 'Error loading project', style=wx.OK | wx.ICON_ERROR)
                md.ShowModal()
                md.Destroy()

                self.NewProject(False)
        else:
            wx.MessageBox('Error: {} is not a valid file'.format(path), 'Invalid File', wx.ICON_ERROR)

    def LoadProjectFromDialog(self):
        fd = wx.FileDialog(wx.GetTopLevelParent(
            self.project_panel), 'Choose a file', wildcard='*.vistas', style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )
        md = wx.MessageDialog(
            wx.GetTopLevelParent(self.project_panel),
            'Are you sure you wish to load this project? You will lose any unsaved changes to your current session.',
            'Load Project', wx.OK | wx.CANCEL
        )

        if fd.ShowModal() == wx.ID_OK and md.ShowModal() == wx.ID_OK:
            self.LoadProject(fd.GetPath())
            return True

        return False

    def AddDataFromFile(self, parent: FolderNode):
        plugins = get_data_plugins()
        extensions = ';'.join('*.{}'.format(x[0]) for x in itertools.chain.from_iterable(x.extensions for x in plugins))

        if not extensions:
            wx.MessageDialog(
                wx.GetTopLevelParent(self.project_panel),
                'There are currently no plugins installed which support file imports', 'Import Error',
                wx.OK | wx.ICON_ERROR
            ).ShowModal()

            return

        fd = wx.FileDialog(
            wx.GetTopLevelParent(self.project_panel), 'Import File', wildcard='Data Files|{}'.format(extensions),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )

        if fd.ShowModal() == wx.ID_OK:
            path = fd.GetPath()
            extension = os.path.splitext(path)[-1].lower().strip('.')
            choices = [x for x in plugins if extension in {y[0] for y in x.extensions}]

            if len(choices) == 1:
                plugin_cls = choices[0]
            else:
                choice_dialog = wx.SingleChoiceDialog(
                    wx.GetTopLevelParent(self.project_panel), 'Choose a plugin to load the data with', 'Plugins',
                    [x.name for x in choices]
                )

                if choice_dialog.ShowModal() == wx.ID_OK:
                    plugin_cls = choices[choice_dialog.GetSelection()]
                else:
                    return

            if not plugin_cls.is_valid_file(path):
                wx.MessageDialog(
                    wx.GetTopLevelParent(self.project_panel), 'Invalid file', 'Invalid file', wx.OK | wx.ICON_ERROR
                ).ShowModal()
            else:
                plugin = plugin_cls()
                plugin.set_path(path)

                thread = CalculateStatsThread(plugin)
                thread.start()
                TaskDialog(wx.GetTopLevelParent(self.project_panel), thread.task, False, False).ShowModal()

                if parent is None:
                    parent = self.project.data_root

                tree_parent = self.RecursiveFindByNode(
                    self.project_panel.data_tree, self.project_panel.data_tree.GetRootItem(), parent
                )
                if not tree_parent.IsOk():
                    tree_parent = self.project_panel.data_tree.GetRootItem()

                tree = self.project_panel.data_tree
                node = DataNode(plugin, plugin.data_name, parent)
                tree.AppendDataItem(tree_parent, node.label, node)

                tree.Expand(tree_parent)

                pce = ProjectChangedEvent(node=node, change=ProjectChangedEvent.ADDED_DATA)
                wx.PostEvent(wx.GetTopLevelParent(self.project_panel), pce)
                self.UpdateTimeline(self.project.data_root)

    def AddVisualization(self, parent):
        allow_3d = parent.type_in_ancestry('scene')
        plugins = get_visualization_plugins() if allow_3d else get_2d_visualization_plugins()

        visualization_dialog = wx.SingleChoiceDialog(
            wx.GetTopLevelParent(self.project_panel), 'Select a visualization to add to this scene:',
            'Add Visualization', [x.name for x in plugins]
        )

        if visualization_dialog.ShowModal() == wx.ID_OK:
            plugin = plugins[visualization_dialog.GetSelection()]()

            tree_parent = self.RecursiveFindByNode(
                self.project_panel.visualization_tree, self.project_panel.visualization_tree.GetRootItem(), parent
            )
            if not tree_parent.IsOk():
                tree_parent = self.project_panel.visualization_tree.GetRootItem()

            node = VisualizationNode(plugin, plugin.name, parent)
            self.project_panel.visualization_tree.AppendVisualizationItem(
                tree_parent, node.label, node
            )

            VisualizationDialog(wx.GetTopLevelParent(self.project_panel), wx.ID_ANY, plugin, self.project, node).Show()

            main_window = wx.GetTopLevelParent(self.project_panel)
            main_window.SetOptions(plugin.get_options(), plugin)

            if isinstance(plugin, VisualizationPlugin3D):
                scene_node = node.parent
                while not scene_node.is_scene:
                    scene_node = scene_node.parent

                plugin.scene = scene_node.scene
                plugin.refresh()

            pce = ProjectChangedEvent(node=node, change=ProjectChangedEvent.ADDED_VISUALIZATION)
            wx.PostEvent(wx.GetTopLevelParent(self.project_panel), pce)

    def AddScene(self, parent):
        ProjectController.scene_count += 1

        scene_name = 'New Scene {}'.format(ProjectController.scene_count)
        node = SceneNode(Scene(scene_name), scene_name, parent)
        tree_parent = self.RecursiveFindByNode(
            self.project_panel.visualization_tree, self.project_panel.visualization_tree.GetRootItem(), parent
        )
        if not tree_parent.IsOk():
            tree_parent = self.project_panel.visualization_tree.GetRootItem()
        tree_item = self.project_panel.visualization_tree.AppendSceneItem(
            tree_parent, node.label, node
        )

        self.project_panel.visualization_tree.Collapse(tree_parent)
        self.project_panel.visualization_tree.EnsureVisible(tree_item)
        self.project_panel.visualization_tree.EditLabel(tree_item)

        edit_ctrl = self.project_panel.visualization_tree.GetEditControl()
        if edit_ctrl is not None:
            edit_ctrl.SetSelection(-1, -1)

        pce = ProjectChangedEvent(node=node, change=ProjectChangedEvent.ADDED_SCENE)
        wx.PostEvent(wx.GetTopLevelParent(self.project_panel), pce)

    def AddFolder(self, parent):
        tree_parent = self.RecursiveFindByNode(
            self.project_panel.data_tree, self.project_panel.data_tree.GetRootItem(), parent
        )
        if tree_parent.IsOk():
            tree = self.project_panel.data_tree
        else:
            tree_parent = self.RecursiveFindByNode(
                self.project_panel.visualization_tree, self.project_panel.visualization_tree.GetRootItem(), parent
            )
            if tree_parent.IsOk():
                tree = self.project_panel.visualization_tree
            else:
                logger.error('Error adding folder: could not determine parent node')
                return

        node = FolderNode('New Folder', parent)
        tree_item = tree.AppendFolderItem(tree_parent, node.label, node)

        tree.Collapse(tree_parent)
        tree.EnsureVisible(tree_item)
        tree.EditLabel(tree_item)

        edit_ctrl = tree.GetEditControl()
        if edit_ctrl is not None:
            edit_ctrl.SetSelection(-1, -1)

        pce = ProjectChangedEvent(node=node, change=ProjectChangedEvent.ADDED_FOLDER)
        wx.PostEvent(wx.GetTopLevelParent(self.project_panel), pce)

    def AddFlythrough(self, parent):
        ProjectController.flythrough_count += 1

        node = FlythroughNode(
            label="Flythrough {}".format(ProjectController.flythrough_count), flythrough=Flythrough(parent.scene)
        )
        tree_parent = self.RecursiveFindByNode(
            self.project_panel.visualization_tree, self.project_panel.visualization_tree.GetRootItem(), parent
        )
        if not tree_parent.IsOk():
            tree_parent = self.project_panel.visualization_tree.GetRootItem()

        tree_item = self.project_panel.visualization_tree.AppendFlythroughItem(tree_parent, node.label, node)

        self.project_panel.visualization_tree.Collapse(tree_parent)
        self.project_panel.visualization_tree.EnsureVisible(tree_item)
        self.project_panel.visualization_tree.EditLabel(tree_item)
        edit_ctrl = self.project_panel.visualization_tree.GetEditControl()
        if edit_ctrl is not None:
            edit_ctrl.SetSelection(-1, -1)

        FlythroughDialog(wx.GetTopLevelParent(self.project_panel), wx.ID_ANY, node.flythrough).Show()

        pce = ProjectChangedEvent(node=node, change=ProjectChangedEvent.ADDED_FLYTHROUGH)
        wx.PostEvent(wx.GetTopLevelParent(self.project_panel), pce)

    def DeleteSelectedItem(self, node, tree, tree_item):
        if node.is_folder:
            message = 'Are you sure you wish to delete this folder? This will also delete any items it contains.'
        elif node.is_scene:
            message = (
                'Are you sure you wish to delete this scene? This will also delete any visualizations it '
                'contains.'
            )
        else:
            message = 'Are you sure you wish to delete this item?'

        md = wx.MessageDialog(wx.GetTopLevelParent(self.project_panel), message, 'Delete?', wx.OK | wx.CANCEL)
        if md.ShowModal() == wx.ID_OK:
            tree.DeleteChildren(tree_item)
            tree.Delete(tree_item)
            self.RecursiveDeleteNode(node)
            self.RefreshTimeline()

            pce = ProjectChangedEvent(node=node, change=ProjectChangedEvent.DELETED_ITEM)
            wx.PostEvent(wx.GetTopLevelParent(self.project_panel), pce)

    def OnTreeKeyDown(self, event):
        tree = event.GetEventObject()

        if event.GetKeyCode() in {wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER}:
            selections = tree.GetSelections()

            if selections:
                if selections[0] == tree.GetRootItem():
                    return

                edit_ctrl = tree.EditLabel(selections[0])
                if edit_ctrl is not None:
                    edit_ctrl.SetSelection(-1, -1)

    def OnTreeItemBeginEdit(self, event):
        tree = event.GetEventObject()

        if event.GetItem() == tree.GetRootItem():
            event.Veto()

    def OnTreeItemEndEdit(self, event):
        tree = event.GetEventObject()
        node = tree.GetItemData(event.GetItem())

        if node is not None:
            if event.IsEditCancelled():
                node.label = event.GetLabel()

            pce = ProjectChangedEvent(node=node, change=ProjectChangedEvent.RENAMED_ITEM)
            wx.PostEvent(wx.GetTopLevelParent(self.project_panel), pce)

    def OnTreeItemRightClick(self, event):
        tree = event.GetEventObject()
        node = tree.GetItemData(event.GetItem())
        popup_menu = ProjectTreeMenu(tree, event.GetItem())

        if node is not None:
            if node != self.project.data_root and node != self.project.visualization_root:
                popup_menu.Append(self.POPUP_RENAME, 'Rename')

            if tree == self.project_panel.data_tree and node.is_folder:
                popup_menu.Append(self.POPUP_ADD_DATA_FILE, 'Add data from file...')

            if tree == self.project_panel.visualization_tree and node.is_folder and not isinstance(node, SceneNode):
                popup_menu.Append(self.POPUP_ADD_SCENE, 'Add scene')

            if tree == self.project_panel.visualization_tree and not node.is_visualization and not node.is_flythrough:
                popup_menu.Append(self.POPUP_ADD_VISUALIZATION, 'Add new visualization')

            if node.is_scene:
                popup_menu.Append(self.POPUP_ADD_FLYTHROUGH, 'Add flythrough')

            if node.is_folder or node.is_scene or event.GetItem() == tree.GetRootItem():
                popup_menu.Append(self.POPUP_ADD_FOLDER, 'Add folder')

            if event.GetItem() != tree.GetRootItem():
                label = 'Delete items' if tree.GetSelections() else 'Delete item'
                popup_menu.Append(self.POPUP_DELETE, label)

        popup_menu.Bind(wx.EVT_MENU, self.OnTreePopupMenu)

        tree.PopupMenu(popup_menu)

    def OnTreePopupMenu(self, event):
        tree = event.GetEventObject().tree
        item = event.GetEventObject().item
        node = tree.GetItemData(item)
        event_id = event.GetId()

        if event_id == self.POPUP_RENAME:
            tree.EditLabel(item)

            edit_ctrl = tree.GetEditControl()
            if edit_ctrl is not None:
                edit_ctrl.SetSelection(-1, -1)

        elif event_id == self.POPUP_ADD_FOLDER:
            self.AddFolder(node)

        elif event_id == self.POPUP_ADD_DATA_FILE:
            self.AddDataFromFile(node)

        elif event_id == self.POPUP_DELETE:
            self.DeleteSelectedItem(node, tree, item)

        elif event_id == self.POPUP_ADD_SCENE:
            self.AddScene(node)

        elif event_id == self.POPUP_ADD_VISUALIZATION:
            self.AddVisualization(node)

        elif event_id == self.POPUP_ADD_FLYTHROUGH:
            self.AddFlythrough(node)

    def OnTreeBeginDrag(self, event):
        item = event.GetItem()

        if item != event.GetEventObject():
            event.Allow()
            self.drag_item = item

    def OnTreeEndDrag(self, event):
        if self.drag_item.IsOk() and event.GetItem().IsOk():
            tree = event.GetEventObject()
            target_item = tree.GetItemData(event.GetItem())
            selections = tree.GetSelections()

            for selection in selections:
                drag_item = tree.GetItemData(selection)
                parent = tree.GetItemParent(selection)

                if (parent.IsOk() and tree.IsSelected(parent)) or target_item == drag_item:
                    continue

                target_root = target_item
                while target_root.parent is not None:
                    target_root = target_root.parent

                    if target_root == drag_item:
                        break

                if target_root == drag_item or target_root.parent is not None:
                    continue

                drag_root = drag_item
                while drag_root.parent is not None:
                    drag_root = drag_root.parent

                if drag_root != target_root:
                    continue

                if target_item.is_folder:
                    drag_item.reparent(target_item)
                    self.RecursiveReparentTreeItem(
                        tree, self.RecursiveFindByNode(tree, tree.GetRootItem(), drag_item),
                        self.RecursiveFindByNode(tree, tree.GetRootItem(), target_item)
                    )

    def OnTreeItemActivate(self, event):
        tree = event.GetEventObject()
        proj_item = tree.GetItemData(event.GetItem())

        if proj_item is not None:
            if proj_item.is_data:
                DataDialog(wx.GetTopLevelParent(self.project_panel), wx.ID_ANY, proj_item.data).ShowModal()

            elif proj_item.is_visualization:
                plugin = proj_item.visualization
                main_window = wx.GetTopLevelParent(self.project_panel)
                main_window.SetOptions(plugin.get_options(), plugin)
                VisualizationDialog(
                    wx.GetTopLevelParent(self.project_panel), wx.ID_ANY, plugin, self.project, proj_item
                ).Show()

            elif proj_item.is_flythrough:
                FlythroughDialog(
                    wx.GetTopLevelParent(self.project_panel), wx.ID_ANY, flythrough=proj_item.flythrough
                ).Show()

            else:
                event.Skip(True)

    def OnTreeItemSelected(self, event):
        node = self.project_panel.visualization_tree.GetItemData(event.GetItem())
        main_window = wx.GetTopLevelParent(self.project_panel)

        if node.is_visualization:
            plugin = node.visualization
            main_window.SetOptions(plugin.get_options(), plugin)

        elif node.is_folder or node.is_scene:
            main_window.SetOptions()

        else:
            event.Skip()

    def RecursiveFindByNode(self, tree, tree_item, node):
        tree_node = tree.GetItemData(tree_item)

        if tree_node == node:
            return tree_item

        elif tree.ItemHasChildren(tree_item):
            child, cookie = tree.GetFirstChild(tree_item)

            while child.IsOk():
                item = self.RecursiveFindByNode(tree, child, node)

                if item.IsOk():
                    return item

                else:
                    child, cookie = tree.GetNextChild(tree_item, cookie)

        return wx.TreeItemId()

    def RecursiveDeleteNode(self, node, delete_root=True):
        if node.is_folder or node.is_scene:
            children = node.children

            for child in children:
                self.RecursiveDeleteNode(child)

        if node.is_data:
            data = node.data

            for visualization in (x.visualization for x in self.project.all_visualizations):
                refresh_visualization = False

                for i in len(visualization.data_roles):
                    if visualization.get_data(i) == data:
                        visualization.set_data(i, None)
                        refresh_visualization = True

                if refresh_visualization and isinstance(visualization, VisualizationPlugin3D):
                    visualization.refresh()

        elif node.is_visualization:
            visualization = node.visualization

            if isinstance(visualization, VisualizationPlugin3D):
                visualization.scene = None

        for item in self.project.exporter.items:
            if node.node_id == item.project_node_id:
                self.project.exporter.remove_item(item)
            elif node.is_flythrough:
                if node.flythrough is item.flythrough:
                    item.flythrough = None

        if delete_root:
            node.delete()

    def UpdateTimeline(self, root):
        timeline = Timeline.app()
        updated = False
        if root.is_data:
            time_info = root.data.time_info
            if time_info is not None and time_info.is_temporal:
                timestamps = time_info.timestamps

                if not timeline.enabled:
                    timeline.start = timestamps[0]
                    timeline.end = timestamps[-1]
                    updated = True

                if timestamps[0] < timeline.start:
                    timeline.start = timestamps[0]

                if timestamps[-1] > timeline.end:
                    timeline.end = timestamps[-1]

                for t in timestamps:
                    timeline.add_timestamp(t)

        elif root.is_folder:
            for child in root.children:
                updated = updated or self.UpdateTimeline(child)
        return updated

    def RefreshTimeline(self):
        timeline = Timeline.app()
        current = timeline.current
        timeline.reset()
        self.UpdateTimeline(self.project.data_root)
        if current >= timeline.start and current <= timeline.end:
            timeline.current = current

    def RecursiveReparentTreeItem(self, tree, item, new_parent):
        node = tree.GetItemData(item)
        new_id = tree.AppendItem(new_parent, tree.GetItemText(item), tree.GetItemImage(item))

        tree.SetItemData(new_id, node)

        if node.is_folder:
            tree.SetItemHasChildren(new_id, True)

        child, cookie = tree.GetFirstChild(item)
        while child.IsOk():
            self.RecursiveReparentTreeItem(tree, child, new_id)

            child, cookie = tree.GetNextChild(item, cookie)

        tree.Delete(item)

    def PopulateTreesFromProject(self, project):
        data_tree = self.project_panel.data_tree
        visualization_tree = self.project_panel.visualization_tree

        data_tree.DeleteChildren(data_tree.GetRootItem())
        data_tree.SetItemData(data_tree.GetRootItem(), project.data_root)
        self.AddTreeChildrenFromNode(project, project.data_root, data_tree, data_tree.GetRootItem())
        data_tree.Expand(data_tree.GetRootItem())

        visualization_tree.DeleteChildren(visualization_tree.GetRootItem())
        visualization_tree.SetItemData(visualization_tree.GetRootItem(), project.visualization_root)
        self.AddTreeChildrenFromNode(
            project, project.visualization_root, visualization_tree, visualization_tree.GetRootItem()
        )
        visualization_tree.Expand(visualization_tree.GetRootItem())

    def AddTreeChildrenFromNode(self, project, node, tree, parent):
        for child in node.children:
            if child.is_data:
                tree.AppendDataItem(parent, child.label, child)

                pce = ProjectChangedEvent(node=node, change=ProjectChangedEvent.ADDED_DATA)
                wx.PostEvent(wx.GetTopLevelParent(self.project_panel), pce)

            elif child.is_visualization:
                tree.AppendVisualizationItem()

            elif child.is_scene:
                tree_item = tree.AppendSceneItem(parent, child.scene.name, child)
                self.AddTreeChildrenFromNode(self.project, child, tree, tree_item)

                ProjectController.scene_count += 1

                pce = ProjectChangedEvent(node=node, change=ProjectChangedEvent.ADDED_SCENE)
                wx.PostEvent(wx.GetTopLevelParent(self.project_panel), pce)

            elif child.is_folder:
                tree_item = tree.AppendFolderItem(parent, child.label, child)
                self.AddTreeChildrenFromNode(project, child, tree, tree_item)
