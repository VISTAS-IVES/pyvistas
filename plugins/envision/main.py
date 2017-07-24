import numpy
import shapely.geometry as geometry
from pyproj import Proj, transform
from OpenGL.GL import *
from vistas.core.graphics.tile import TileGridRenderable
from vistas.core.graphics.features import FeatureCollection
from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.option import Option, OptionGroup
from vistas.core.plugins.visualization import VisualizationPlugin3D
from vistas.ui.utils import *

# Todo - revise shader to use a single light position


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

        self._needs_tiles = False
        self._scene = None
        self._zoom = Option(self, Option.SLIDER, "Zoom Level", 10, 5, 12, 1)

    def update_option(self, option=None):
        if option.plugin is not self:
            return

        print("Changed zoom")


    def get_options(self):
        options = OptionGroup()
        options.items.append(self._zoom)
        return options

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
        self._needs_tiles = True

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

        if self._needs_tiles:
            self._create_terrain_mesh()
            self._needs_tiles = False

        if self.feature_collection is not None:
            if self.feature_collection.can_render:
                print('Woo! We got some cool stuff')
                self.feature_collection.transfer_to_scene(self.scene)

        post_redisplay()

    def _create_terrain_mesh(self):
        if self.data is not None:
            self.tile_renderable = TileGridRenderable(self.data.extent, True)
            self.scene.add_object(self.tile_renderable)
            self.feature_collection = FeatureCollection(self.data.get_features(), self.data.extent,
                                                        self.tile_renderable.mercator_bounds, self.tile_renderable.cellsize)
            #triangles = self.feature_collection.mercator_triangles
            #print(next(triangles))

            self._needs_tiles = False
