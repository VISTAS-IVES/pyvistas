import mercantile
from pyproj import Proj
from pyrr import Vector3

from vistas.core.gis.elevation import ElevationService, TILE_SIZE
from vistas.core.graphics.geometries import TerrainTileGeometry
from vistas.core.graphics.mesh import Mesh
from vistas.core.graphics.shaders import TerrainTileShaderProgram
from vistas.core.task import Task
from vistas.core.threading import Thread
from vistas.ui.utils import post_redisplay


class TerrainTileWorker(Thread):

    def __init__(self, factory):
        super().__init__()
        self.factory = factory
        self.task = Task("Generating Terrain Tiles")

    def run(self):
        self.init_event_loop()
        e = ElevationService()
        e.zoom = self.factory.zoom
        self.task.status = Task.RUNNING
        e.get_tiles(self.factory.wgs84, self.task)
        grids = e.create_data_dem(self.factory.extent, self.factory.zoom)

        for tile in self.factory.tiles:
            data = grids[tile].T
            self.sync_with_main(self.factory.add_tile(tile, data), block=True)
            self.sync_with_main(post_redisplay)
            self.task.inc_progress()

        self.sync_with_main(self.factory.resolve_seams, block=True)

        self.task.status = Task.COMPLETE
        self.sync_with_main(post_redisplay)


class TerrainTileFactory:
    """ A factory for generating TerrainTileGeometry from an elevation source. """

    shader = None

    def __init__(self, extent, initial_zoom=10):
        if self.shader is None:
            self.shader = TerrainTileShaderProgram()

        self.extent = extent
        self.wgs84 = extent.project(Proj(init='EPSG:4326'))
        self._zoom = None
        self.tiles = []
        self.meshes = {}
        self._ul = None
        self._br = None
        self._scene = None
        self.zoom = initial_zoom

    def build(self):
        TerrainTileWorker(self).start()

    def add_to(self, scene):
        self._scene = scene
        self.build()

    @property
    def zoom(self):
        return self._zoom

    @zoom.setter
    def zoom(self, zoom):
        if zoom != self._zoom:
            self._zoom = zoom
            self.tiles = list(mercantile.tiles(*self.wgs84.as_list(), [self.zoom]))
            self._ul = self.tiles[0]
            self._br = self.tiles[-1]
            if self._scene:

                # Todo - remove current tile meshes and dispose of them

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

    def add_tile(self, mtile, heights):
        geometry = TerrainTileGeometry(mtile, heights)
        tile_mesh = Mesh(geometry, self.shader)
        right = (mtile.x - self._ul.x) * TILE_SIZE
        down = (mtile.y - self._ul.y) * TILE_SIZE
        tile_mesh.position = Vector3([right, down, 0.0])
        self.meshes[mtile] = tile_mesh
        if self._scene:
            self._scene.add_object(tile_mesh)

    def resolve_seams(self):
        pass    # Todo - resolve seams for current meshes