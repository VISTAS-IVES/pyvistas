from pyrr import Vector3

from vistas.core.gis.elevation import ElevationService, TILE_SIZE
from vistas.core.graphics.factory import MapMeshFactory, MeshFactoryWorker
from vistas.core.graphics.mesh import Mesh
from vistas.core.graphics.terrain.geometry import TerrainTileGeometry
from vistas.core.graphics.terrain.shader import TerrainTileShaderProgram


class TerrainTileWorker(MeshFactoryWorker):

    task_name = "Building Terrain"

    def work(self):
        grids = ElevationService().create_data_dem(self.factory.extent, self.factory.zoom)
        for tile in self.factory.tiles:
            if tile not in grids:       # Race condition
                return
            data = grids[tile]
            self.sync_with_main(self.factory.add_tile, (tile, data), block=True)
            self.task.inc_progress()
        self.sync_with_main(self.factory.resolve_seams, block=True)


class TerrainTileFactory(MapMeshFactory):
    """ A MapMeshFactory for generating terrain from an ElevationSource. """

    worker_class = TerrainTileWorker

    def __init__(self, extent, shader=None, plugin=None, initial_zoom=10):
        if shader is None:
            shader = TerrainTileShaderProgram()
        super().__init__(extent, shader, plugin, initial_zoom)

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
