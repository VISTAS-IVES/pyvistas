import mercantile
from pyproj import Proj
from pyrr import Vector3

from vistas.core.gis.elevation import ElevationService, TILE_SIZE
from vistas.core.graphics.factory import MeshFactory, MeshFactoryWorker
from vistas.core.graphics.mesh import Mesh
from vistas.ui.utils import post_redisplay
from vistas.core.graphics.terrain.geometry import TerrainTileGeometry
from vistas.core.graphics.terrain.shader import TerrainTileShaderProgram


class TerrainTileWorker(MeshFactoryWorker):

    task_name = "Generating Tile Meshes"

    def work(self):
        grids = ElevationService().create_data_dem(self.factory.extent, self.factory.zoom)
        for tile in self.factory.tiles:
            if tile not in grids:       # Race condition
                return
            data = grids[tile]
            self.sync_with_main(self.factory.add_tile, (tile, data), block=True)
            self.task.inc_progress()

        self.sync_with_main(self.factory.resolve_seams, block=True)
        self.sync_with_main(post_redisplay)


class TerrainTileFactory(MeshFactory):
    """ A MeshFactory for generating terrain from an ElevationSource. """

    worker_class = TerrainTileWorker

    def __init__(self, extent, shader=None, plugin=None, initial_zoom=10):
        super().__init__()
        if shader is None:
            shader = TerrainTileShaderProgram()
        self.shader = shader
        self.plugin = plugin
        self.extent = extent
        self._zoom = None
        self.tiles = []
        self._ul = None
        self._br = None
        self.zoom = initial_zoom

    @property
    def zoom(self):
        return self._zoom

    @zoom.setter
    def zoom(self, zoom):
        if zoom != self._zoom:
            self._zoom = zoom
            self.tiles = list(mercantile.tiles(*self.extent.project(Proj(init='EPSG:4326')).as_list(), [self.zoom]))
            self._ul = self.tiles[0]
            self._br = self.tiles[-1]

            # Destroy these meshes
            if self.items:
                for obj in self.items:
                    obj.geometry.dispose()
                del self.items[:]

            # Now build new meshes
            self.build()

    @property
    def mercator_bounds(self):
        ul_bounds = mercantile.xy_bounds(self._ul)
        br_bounds = mercantile.xy_bounds(self._br)
        return mercantile.Bbox(ul_bounds.left, br_bounds.bottom, br_bounds.right, ul_bounds.top)

    @property
    def geographic_bounds(self):
        ul_bounds = mercantile.bounds(self._ul)
        br_bounds = mercantile.bounds(self._br)
        return mercantile.LngLatBbox(ul_bounds.west, br_bounds.south, br_bounds.east, ul_bounds.north)

    def add_tile(self, tile, heights):
        tile_mesh = Mesh(TerrainTileGeometry(tile, heights), self.shader, plugin=self.plugin)
        right = (tile.y - self._ul.y) * (TILE_SIZE - 1)
        down = (tile.x - self._ul.x) * (TILE_SIZE - 1)
        tile_mesh.position = Vector3([right, down, 0.0])
        tile_mesh.update()
        self.items.append(tile_mesh)
        self.update()

    def resolve_seams(self):
        pass    # Todo
