import numpy
import shapely.geometry as geometry
from OpenGL.GL import *
from pyrr import Vector3, Vector4
from pyrr.vector3 import generate_normals
from rasterio import features
from rasterio import transform
from pyproj import Proj
from vistas.core.gis.elevation import ElevationService
from vistas.core.graphics.tile import TileMesh, TileRenderable
from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.option import Option, OptionGroup
from vistas.core.plugins.visualization import VisualizationPlugin3D
from vistas.ui.utils import *


class EnvisionVisualization(VisualizationPlugin3D):

    id = 'envision_tiles_viz'
    name = 'Envision'
    description = 'Terrain visualization with tiles'
    author = 'Conservation Biology Institute'
    version = '1.0'
    visualization_name = 'Envision (Tiles)'

    def __init__(self):
        super().__init__()

        self.tiles = []
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

        if self.data:

            print(self.data.extent.as_list())

        self._needs_tiles = True

    def get_data(self, role):
        return self.data

    @property
    def scene(self):
        return self._scene

    @scene.setter
    def scene(self, scene):
        if self._scene is not None:
            if self.tiles:
                for tile in self.tiles:
                    self._scene.remove_object(tile)

        self._scene = scene

        if self.tiles and self._scene is not None:
            for tile in self.tiles:
                self._scene.add_object(tile)

    def refresh(self):

        if self._needs_tiles:
            self._create_terrain_mesh()
            self._needs_tiles = False

        post_redisplay()

    def _create_terrain_mesh(self):
        if self.data is not None:

            e = ElevationService()
            e._zoom = 10
            tiles = e.tiles(self.data.extent, 10)

            e.get_tiles(self.data.extent.project(Proj(init='EPSG:4326')), None)

            t = list(tiles)[0]
            t_data = e.get_grid(t.x, t.y, 10).T
            tile = TileRenderable(30)
            tile.tile.set_tile_data(t_data)
            tile.bounding_box = tile.tile.bounding_box

            self.tiles.append(tile)
            self.scene.add_object(tile)

            self._needs_tiles = False
