import json
import os

import wx
from pyrr import Matrix44

from vistas.core.color import RGBColor
from vistas.core.export import Exporter
from vistas.core.graphics.flythrough import Flythrough, FlythroughPoint
from vistas.core.graphics.scene import Scene
from vistas.core.plugins.interface import Plugin
from vistas.core.plugins.visualization import VisualizationPlugin3D
from vistas.core.timeline import Timeline
from vistas.ui.utils import post_message

SAVE_FILE_VERSION = 1


class ProjectNode:
    """
    An interface for containing information about a single project item. Subclasses determine the node's contents (i.e.
    data/visualization plugins, scenes, flythroughs). ProjectNodes also provide methods for serialization when saving
    project contents.
    """
    next_id = 1
    node_type = ''

    def __init__(self, label=None, parent=None, node_id=None):
        self.dirty = True
        self.label = label
        self.parent = parent

        if node_id is not None:
            self.node_id = node_id
            if node_id >= ProjectNode.next_id:
                ProjectNode.next_id = node_id + 1
        else:
            self.node_id = ProjectNode.next_id
            ProjectNode.next_id += 1

        if parent is not None:
            parent.add_child(self)

    def delete(self):
        if self.parent is not None:
            self.parent.remove_child(self)

    @property
    def is_folder(self):
        return isinstance(self, FolderNode)

    @property
    def is_data(self):
        return isinstance(self, DataNode)

    @property
    def is_visualization(self):
        return isinstance(self, VisualizationNode)

    @property
    def is_scene(self):
        return self.__class__ == SceneNode

    @property
    def is_flythrough(self):
        return isinstance(self, FlythroughNode)

    @property
    def is_dirty(self):
        return self.dirty

    @is_dirty.setter
    def is_dirty(self, dirty):
        self.dirty = dirty

    def reparent(self, parent):
        if self.parent is not None:
            self.parent.remove_child(self)

        self.parent = parent
        if parent is not None:
            parent.add_child(self)

    def serialize(self, path=None):
        return {
            'type': self.node_type,
            'id': self.node_id,
            'label': self.label
        }

    @classmethod
    def load(cls, data, path=None):
        pass  # Implemented by subclasses


class FolderNode(ProjectNode):
    """
    A subclass of ProjectNode that contains a list of other ProjectNodes, or 'children'. Provides an interface for
    obtaining child nodes of different types.
    """
    node_type = 'folder'

    def __init__(self, label, *args, **kwargs):
        super().__init__(label, *args, **kwargs)

        self.children = []

    @property
    def is_dirty(self):
        if self.dirty:
            return True

        return any(x.is_dirty for x in self.children)

    @is_dirty.setter
    def is_dirty(self, dirty):
        self.dirty = dirty
        for x in self.children:
            x.is_dirty = dirty

    def add_child(self, child):
        self.children.append(child)
        self.dirty = True

    def remove_child(self, child):
        if child in self.children:
            self.children.remove(child)
            self.dirty = True

    @property
    def visualization_nodes(self):
        nodes = [x for x in self.children if x.is_visualization]

        for child in (x for x in self.children if x.is_folder):
            nodes += child.visualization_nodes

        return nodes

    @property
    def scene_nodes(self):
        nodes = [x for x in self.children if x.is_scene]

        for child in (x for x in self.children if x.is_folder):
            nodes += child.scene_nodes

        return nodes

    @property
    def data_nodes(self):
        nodes = [x for x in self.children if x.is_data]

        for child in (x for x in self.children if x.is_folder):
            nodes += child.data_nodes

        return nodes

    @property
    def scene_nodes(self):
        nodes = [x for x in self.children if x.is_scene]

        for child in (x for x in self.children if x.is_folder):
            nodes += child.scene_nodes

        return nodes

    @property
    def flythrough_nodes(self):
        nodes = [x for x in self.children if x.is_flythrough]

        for child in (x for x in self.children if x.is_folder):
            nodes += child.flythrough_nodes

        return nodes

    def serialize(self, path=None):
        data = super().serialize(path)
        data.update({
            'children': [x.serialize(path) for x in self.children]
        })

        return data

    @classmethod
    def load(cls, data, path=None):
        folder = cls(data.get('label'), data.get('parent'), data.get('id'))

        for child in data.get('children', []):
            child['parent'] = folder
            NODE_TYPES[child['type']].load(child, path)

        return folder

    def type_in_ancestry(self, node_type):
        if self.node_type == node_type:
            return True
        elif self.parent is None:
            return False
        else:
            return self.parent.type_in_ancestry(node_type)


class DataNode(ProjectNode):
    """ A subclass of ProjectNode that contains a reference to a data plugin. """
    node_type = 'data'

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._data = data

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value
        self.dirty = True

    def serialize(self, path=None):
        data = super().serialize(path)
        data.update({
            'plugin': self.data.id,
            'absolute_path': os.path.abspath(self.data.path),
            'relative_path': os.path.relpath(self.data.path, os.path.dirname(path))
        })

        return data

    @classmethod
    def load(cls, data, path=None):
        plugin = Plugin.by_name(data['plugin'])()
        abs_path = data['absolute_path']
        rel_path = os.path.join(path, data['relative_path'])

        if os.path.exists(rel_path):
            data_path = rel_path
        elif os.path.exists(abs_path):
            data_path = abs_path
        else:
            post_message("Could not find data for plugin {} at path {}".format(plugin.name, abs_path), 1)
            md = wx.MessageDialog(None, "Would you like to attempt to repair the path to the missing data?",
                                  "Data Not Found", wx.ICON_ERROR | wx.YES_NO)

            extensions = ';'.join('*.{}'.format(x[0]) for x in plugin.extensions)
            fd = wx.FileDialog(None, "Import File", wildcard='Data Files|{}'.format(extensions),
                               style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_DEFAULT_STYLE)

            if md.ShowModal() == wx.ID_YES and fd.ShowModal() == wx.ID_OK:
                data_path = fd.GetPath()
            else:
                raise OSError("Could not repair data path.")

        plugin.set_path(data_path)
        plugin.calculate_stats()

        return cls(plugin, data.get('label'), data.get('parent'), data.get('id'))


class VisualizationNode(ProjectNode):
    """ A subclass of ProjectNode that contains a reference to a visualization plugin. """
    node_type = 'visualization'

    def __init__(self, visualization=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._visualization = visualization

    @property
    def visualization(self):
        return self._visualization

    @visualization.setter
    def visualization(self, value):
        self._visualization = value
        self.dirty = True

    def serialize(self, path=None):
        data = super().serialize()

        data_info = []
        for i, pair in enumerate(self.visualization.data_roles):
            data_type, name = pair

            if self.visualization.role_supports_multiple_inputs(i):
                plugins = self.visualization.get_multiple_data(i)
            else:
                plugins = [self.visualization.get_data(i)]

            for p in plugins:
                data_node = Project.get().find_data_node(p)
                if data_node is None:
                    node_id = None
                else:
                    node_id = data_node.node_id
                data_info.append({
                    'type': data_type,
                    'role': name,
                    'data_id': node_id,
                    'role_id': i
                })

        options = self.visualization.get_options()
        if options is not None:
            options = options.serialize()

        data.update({
            'plugin': self.visualization.id,
            'data': data_info,
            'options': options
        })

        return data

    @classmethod
    def load(cls, data, path=None):
        plugin = Plugin.by_name(data['plugin'])()

        if isinstance(plugin, VisualizationPlugin3D):
            plugin.scene = data.get('parent').scene

        # Load data sources
        idx = 0
        for i, pair in enumerate(plugin.data_roles):
            dtype, role = pair
            data_info = data['data'][idx]
            idx += 1
            node_data = [data_info]
            if plugin.role_supports_multiple_inputs(i):
                while idx < len(data['data']) and data['data'][idx]['role_id'] == i:
                    node_data.append(data['data'][idx])
                    idx += 1

            for node in node_data:
                data_id = node['data_id']
                if node['role'] == role and node['type'] == dtype:
                    data_node = Project.get().get_node_by_id(data_id)
                    if data_node is not None:
                        plugin.set_data(data_node.data, i)

        # Load option values
        options = data['options']
        if options is not None:
            for option in plugin.get_options().flat_list:
                for option_data in options:
                    if option_data['name'] == option.name and option_data['option_type'] == option.option_type:
                        value = option_data['value']
                        if option.option_type is option.COLOR:
                            option.value = RGBColor(*value)
                        else:
                            option.value = value
                        break

        # Let plugin data and options take effect
        if isinstance(plugin, VisualizationPlugin3D):
            plugin.refresh()

        return cls(plugin, data.get('label'), data.get('parent'), data.get('id'))


class SceneNode(FolderNode):
    """ A subclass of ProjectNode that contains a reference to a Scene. """
    node_type = 'scene'

    def __init__(self, scene=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._scene = scene

    @property
    def scene(self):
        return self._scene

    @scene.setter
    def scene(self, value):
        self._scene = value
        self.dirty = True

    @classmethod
    def load(cls, data, path=None):
        scene = cls(Scene(data.get('label')), data.get('label'), data.get('parent'), data.get('id'))

        for child in data.get('children', []):
            child['parent'] = scene
            NODE_TYPES[child['type']].load(child)

        return scene


class FlythroughNode(ProjectNode):
    """ A subclass of ProjectNode that contains a reference to a Flythrough. """
    node_type = 'flythrough'

    def __init__(self, flythrough=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._flythrough = flythrough

    @property
    def flythrough(self):
        return self._flythrough

    @flythrough.setter
    def flythrough(self, value):
        self._flythrough = value
        self.dirty = True

    def serialize(self, path=None):
        data = super().serialize()

        keyframes = []
        for frame in self.flythrough.keyframe_indices:
            self.flythrough.update_camera_to_keyframe(frame)
            keyframes.append({
                'index': frame,
                'matrix': self.flythrough.camera.matrix.tolist()
            })

        data.update({
            'fps': self.flythrough.fps,
            'length': self.flythrough.length,
            'keyframes': keyframes,
        })

        return data

    @classmethod
    def load(cls, data, path=None):
        node = cls(
            Flythrough(data.get('parent').scene, data.get('fps', 30), data.get('length', 60)),
            data.get('label'), data.get('parent'), data.get('id')
        )

        flythrough = node.flythrough
        keyframes = data.get('keyframes', [])
        for frame in keyframes:
            matrix = Matrix44(frame['matrix'])
            flythrough.camera.matrix = matrix
            point = FlythroughPoint(
                flythrough.camera.get_position(),
                flythrough.camera.get_direction(),
                flythrough.camera.get_up_vector()
            )
            flythrough.add_keyframe(frame['index'], point)
        flythrough.update_camera_to_keyframe(0)

        return node


NODE_TYPES = {
    'folder': FolderNode,
    'data': DataNode,
    'visualization': VisualizationNode,
    'scene': SceneNode,
    'flythrough': FlythroughNode
}


class Project:
    """
    An interface for accessing information about a project's active ProjectNodes. Projects are also responsible for
    orchestrating serialization and deserialization routines when saving and loading projects from disk, including data
    migrations and handling exceptions.
    """

    current_project = None

    def __init__(self, name='Untitled Project'):
        self.name = name
        self.data_root = FolderNode('Project Data')
        self.visualization_root = FolderNode('Project Visualizations')
        self.exporter = Exporter()

    @property
    def is_dirty(self):
        return self.data_root.is_dirty or self.visualization_root.is_dirty

    @is_dirty.setter
    def is_dirty(self, dirty):
        self.data_root.is_dirty = dirty
        self.visualization_root.is_dirty = dirty

    @classmethod
    def get(cls):
        """ Get global current project """

        if cls.current_project is None:
            cls.current_project = Project()

        return cls.current_project

    def make_current(self):
        """ Set this project as the global current project """

        Project.current_project = self

    def save(self, path):
        if os.path.exists(path):
            os.remove(path)

        self.name = os.path.split(path)[-1]

        data = {
            'version': SAVE_FILE_VERSION,
            'name': self.name,
            'data_root': self.data_root.serialize(path),
            'visualization_root': self.visualization_root.serialize(),
            'exporter': self.exporter.serialize(),
            'timeline_filter': Timeline.app().serialize_filter()
        }

        with open(path, 'w') as f:
            json.dump(data, f)

        self.is_dirty = False

    def load(self, path, controller):

        with open(path) as f:
            data = json.load(f)

        # Migrate imported data to latest version
        if data['version'] < SAVE_FILE_VERSION:
            self.migrate(data)

        self.name = data['name']
        self.data_root = FolderNode.load(data['data_root'], os.path.dirname(path))
        controller.RefreshTimeline()
        Timeline.app().load_filter(data.get('timeline_filter', None))
        self.visualization_root = FolderNode.load(data['visualization_root'])
        self.exporter = Exporter.load(data.get('exporter', None), self)
        self.is_dirty = False

    def migrate(self, data):
        pass    # No migrations yet

    @property
    def all_visualizations(self):
        return self.visualization_root.visualization_nodes

    @property
    def all_data(self):
        return self.data_root.data_nodes

    @property
    def all_scenes(self):
        return self.visualization_root.scene_nodes

    def get_node_by_id(self, id) -> ProjectNode:
        node = self._get_node_by_id(self.data_root, id)
        if node is None:
            node = self._get_node_by_id(self.visualization_root, id)
        return node

    @staticmethod
    def _get_node_by_id(node: FolderNode, id):
        if node.node_id == id:
            return node
        else:
            for child in node.children:
                if child.node_id == id:
                    return child
                else:
                    if child.node_type == 'folder' or child.node_type == 'scene':
                        result = Project._get_node_by_id(child, id)
                        if result is not None:
                            return result
        return None

    def find_viz_with_parent_scene(self, parent_scene: Scene):
        scene_node = self._recursive_find_scene_node(self.visualization_root, parent_scene)
        visualizations = []
        if scene_node is not None:
            self._recursive_add_all_viz(scene_node, visualizations)
        return visualizations

    @staticmethod
    def _recursive_add_all_viz(root: FolderNode, visualizations):
        for child in root.children:
            if child.is_folder:
                Project._recursive_add_all_viz(child, visualizations)
            if child.is_visualization:
                visualizations.append(child.visualization)

    @staticmethod
    def _recursive_find_scene_node(root: FolderNode, scene):
        for child in root.children:
            if child.is_folder:
                scene_node = Project._recursive_find_scene_node(child, scene)
                if scene_node is not None:
                    return scene_node
            if child.is_scene and child.scene is scene:
                return child
        return None

    def find_data_node(self, data_plugin):
        for node in self.data_root.data_nodes:
            if node.data is data_plugin:
                return node
        return None

    def find_flythrough_node(self, flythrough):
        for node in self.visualization_root.flythrough_nodes:
            if node.flythrough is flythrough:
                return node
        return None

    def find_visualization_node(self, visualization):
        for node in self.visualization_root.visualization_nodes:
            if node.visualization is visualization:
                return node
        return None
