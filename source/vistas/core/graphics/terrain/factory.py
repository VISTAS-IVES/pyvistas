from mercantile import Tile
from numpy import arange
from pyrr import Vector3

from vistas.core.gis.elevation import ElevationService, TILE_SIZE, meters_per_px
from vistas.core.graphics.factory import MapMeshFactory, MeshFactoryWorker, use_event_loop
from vistas.core.graphics.mesh import Mesh
from vistas.core.graphics.terrain.geometry import TerrainTileGeometry
from vistas.core.graphics.terrain.shader import TerrainTileShaderProgram


class TerrainTileWorker(MeshFactoryWorker):

    task_name = "Building Terrain"

    @use_event_loop
    def run(self):
        grids = ElevationService().create_data_dem(self.factory.extent, self.factory.zoom)
        for tile in self.factory.tiles:
            if tile not in grids:       # Race condition
                return
            data = grids[tile]
            data /= meters_per_px(tile.z)
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
        tile_indices = arange(TILE_SIZE ** 2)
        left_indices = tile_indices[::TILE_SIZE]
        bottom_indices = tile_indices[TILE_SIZE**2 - TILE_SIZE:]
        right_indices = tile_indices[TILE_SIZE - 1::TILE_SIZE]
        top_indices = tile_indices[:TILE_SIZE]

        for mesh in self.items:
            geometry = mesh.geometry
            t = geometry.tile

            left = Tile(t.x - 1, t.y, t.z)
            bottom = Tile(t.x, t.y + 1, t.x)
            right = Tile(t.x + 1, t.y, t.z)
            top = Tile(t.x, t.y - 1, t.z)

            neighborhood = [x.geometry for x in self.items if x.geometry.tile in (left, bottom, right, top)]
            if neighborhood:
                heights = geometry.heights.ravel()
                for neighbor in neighborhood:
                    ntile = neighbor.tile
                    if ntile == left:
                        indices = left_indices
                        neighbor_indices = right_indices
                    elif ntile == bottom:
                        indices = bottom_indices
                        neighbor_indices = top_indices
                    elif ntile == right:
                        indices = right_indices
                        neighbor_indices = left_indices
                    elif ntile == top:
                        indices = top_indices
                        neighbor_indices = bottom_indices
                    else:
                        raise ValueError("Neighbor is not a neighbor!")
                    neighbor_heights = neighbor.heights.ravel()
                    heights[indices] = neighbor_heights[neighbor_indices]

                geometry.heights = heights.reshape((TILE_SIZE, TILE_SIZE))
