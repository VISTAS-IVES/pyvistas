from vistas.core.graphics.features import FeatureCollection
from vistas.core.graphics.tile import TileLayerRenderable
from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.visualization import VisualizationPlugin3D
from vistas.ui.utils import *

# Todo - revise tile shader to use a single light position


class EnvisionVisualization(VisualizationPlugin3D):

    id = 'envision_tiles_viz'
    name = 'Envision'
    description = 'Terrain visualization with tiles'
    author = 'Conservation Biology Institute'
    version = '1.0'
    visualization_name = 'Envision (Tiles)'

    def __init__(self):
        super().__init__()

        self.tile_renderable = None
        self.feature_collection = None
        self.data = None

        self._needs_mesh = False
        self._scene = None

    @property
    def can_visualize(self):
        return self.data is not None

    @property
    def data_roles(self):
        return [
            (DataPlugin.FEATURE, 'Shapefile')
        ]

    def set_data(self, data: DataPlugin, role):
        self.data = data
        self._needs_mesh = True

    def get_data(self, role):
        return self.data

    @property
    def scene(self):
        return self._scene

    @scene.setter
    def scene(self, scene):
        if self._scene is not None:
            if self.tile_renderable:
                self._scene.remove_object(self.tile_renderable)

        self._scene = scene

        if self.tile_renderable and self._scene is not None:
            self._scene.add_object(self.tile_renderable)

    def refresh(self):
        if self._needs_mesh:
            self._create_terrain_mesh()
            self._needs_mesh = False
        post_redisplay()

    def _create_terrain_mesh(self):
        if self.data is not None:
            zoom = 10
            self.tile_renderable = TileLayerRenderable(self.data.extent, zoom=zoom)
            self.scene.add_object(self.tile_renderable)
            self.feature_collection = FeatureCollection(self.data, self.tile_renderable.cellsize, zoom=zoom)
            self.feature_collection.render(self.scene)
