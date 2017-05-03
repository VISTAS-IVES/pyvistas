import json
import os

from vistas.core.graphics.scene import Scene
from vistas.core.plugins.interface import Plugin

SAVE_FILE_VERSION = 1


class ProjectNode:
    next_id = 1
    node_type = ''

    def __init__(self, label, parent=None, node_id=None):
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
        return isinstance(self, SceneNode)

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
            'plugin': self.data.name,
            'path': self.data.path
        })

        return data

    @classmethod
    def load(cls, data):
        plugin = Plugin.by_name(data['plugin'])
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
        data.update({
            'plugin': self.visualization.name,
            'data': {}  # Todo: data roles
        })

    @classmethod
    def load(cls, data):
        pass  # Todo


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

    @classmethod
    def load(cls, data):
        return cls()  # Todo


NODE_TYPES = {
    'folder': FolderNode,
    'data': DataNode,
    'visualization': VisualizationNode,
    'flythrough': FlythroughNode
}


class Project:
    current_project = None

    def __init__(self, name='Untitled Project'):
        self.name = name
        self.data_root = FolderNode('Project Data')
        self.visualization_root = FolderNode('Project Visualizations')
        self.exporter = object()  # Todo: VI_Exporter()

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
            'visualization_root': self.visualization_root.serialize()
        }

        with open(path, 'w') as f:
            json.dump(data, f)

    def load(self, path):
        # Todo: check for old, sqlite save

        with open(path) as f:
            data = json.load(f)

        # Todo: save file migration

        self.name = data['name']
        self.data_root = FolderNode.load(data['data_root'])
        self.visualization_root = FolderNode.load(data['visualization_root'])

        # Todo: export configuration, timeline filter

    @property
    def all_visualizations(self):
        return []  # Todo
