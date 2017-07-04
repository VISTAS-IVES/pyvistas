import json
import os

from pyrr import Matrix44
from vistas.core.graphics.scene import Scene
from vistas.core.graphics.flythrough import Flythrough, FlythroughPoint
from vistas.core.color import RGBColor
from vistas.core.plugins.interface import Plugin
from vistas.core.plugins.visualization import VisualizationPlugin3D
from vistas.core.export import Exporter
from vistas.core.timeline import Timeline

SAVE_FILE_VERSION = 1


class ProjectNode:
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

    def reparent(self, parent):
        if self.parent is not None:
            self.parent.remove_child(self)

        self.parent = parent
        if parent is not None:
            parent.add_child(self)

    def serialize(self):
        return {
            'type': self.node_type,
            'id': self.node_id,
            'label': self.label
        }

    @classmethod
    def load(cls, data):
        pass  # Implemented by subclasses


class FolderNode(ProjectNode):
    node_type = 'folder'

    def __init__(self, label, *args, **kwargs):
        super().__init__(label, *args, **kwargs)

        self.children = []

    @property
    def is_dirty(self):
        if self.dirty:
            return True

        return any(x.is_dirty() for x in self.children)

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

    def serialize(self):
        data = super().serialize()
        data.update({
            'children': [x.serialize() for x in self.children]
        })

        return data

    @classmethod
    def load(cls, data):
        folder = cls(data.get('label'), data.get('parent'), data.get('id'))

        for child in data.get('children', []):
            child['parent'] = folder
            NODE_TYPES[child['type']].load(child)

        return folder

    def type_in_ancestry(self, node_type):
        return (
            self.node_type == node_type or
            any(x.node_type for x in self.children) or
            any(x.type_in_ancestry for x in self.children if isinstance(x, FolderNode))
        )


class DataNode(ProjectNode):
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

    def serialize(self):
        data = super().serialize()
        data.update({
            'plugin': self.data.id,
            'path': self.data.path
        })

        return data

    @classmethod
    def load(cls, data):
        plugin = Plugin.by_name(data['plugin'])()
        plugin.set_path(data['path'])

        return cls(plugin, data.get('label'), data.get('parent'), data.get('id'))


class VisualizationNode(ProjectNode):
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

    def serialize(self):
        data = super().serialize()

        data_info = []
        for i, pair in enumerate(self.visualization.data_roles):
            data_type, name = pair
            data_node = Project.get().find_data_node(self.visualization.get_data(i))
            if data_node is None:
                node_id = None
            else:
                node_id = data_node.node_id
            data_info.append({
                'type': data_type,
                'role': name,
                'data_id': node_id
            })

        data.update({
            'plugin': self.visualization.id,
            'data': data_info,
            'options': self.visualization.get_options().serialize()
        })

        return data

    @classmethod
    def load(cls, data):
        plugin = Plugin.by_name(data['plugin'])()

        if isinstance(plugin, VisualizationPlugin3D):
            plugin.scene = data.get('parent').scene

        # Load data sources
        for i, pair in enumerate(plugin.data_roles):
            dtype, role = pair
            data_info = data['data'][i]
            data_id = data_info['data_id']
            if data_info['role'] == role and data_info['type'] == dtype:

                data_node = Project.get().get_node_by_id(data_id)
                if data_node is not None:
                    plugin.set_data(data_node.data, i)

        # Load option values
        options = data['options']
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
    def load(cls, data):
        scene = cls(Scene(data.get('label')), data.get('label'), data.get('parent'), data.get('id'))

        for child in data.get('children', []):
            child['parent'] = scene
            NODE_TYPES[child['type']].load(child)

        return scene


class FlythroughNode(ProjectNode):
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

    def serialize(self):
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
    def load(cls, data):
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
    current_project = None

    def __init__(self, name='Untitled Project'):
        self.name = name
        self.data_root = FolderNode('Project Data')
        self.visualization_root = FolderNode('Project Visualizations')
        self.exporter = Exporter()
        self.dirty = False

    @property
    def is_dirty(self):
        return self.dirty or self.data_root.is_dirty or self.visualization_root.is_dirty

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
            'data_root': self.data_root.serialize(),
            'visualization_root': self.visualization_root.serialize(),
            'exporter': self.exporter.serialize(),
            'timeline_filter': Timeline.app().serialize_filter()
        }

        with open(path, 'w') as f:
            json.dump(data, f)

    def load(self, path):
        # Todo: check for old, sqlite save

        with open(path) as f:
            data = json.load(f)

        # Migrate imported data to latest version
        if data['version'] < SAVE_FILE_VERSION:
            self.migrate(data)

        self.name = data['name']
        self.data_root = FolderNode.load(data['data_root'])
        self.visualization_root = FolderNode.load(data['visualization_root'])
        self.exporter = Exporter.load(data.get('exporter', None))
        Timeline.app().load_filter(data.get('timeline_filter', None))

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
                    if child.node_type == 'folder':
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
