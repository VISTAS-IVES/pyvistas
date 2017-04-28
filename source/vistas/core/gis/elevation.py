import mercantile
import aiohttp
import asyncio
import os
import numpy
from PIL import Image
from pyproj import Proj, transform
from io import BytesIO
from vistas.core.plugins.data import DataPlugin
from vistas.core.paths import get_resources_directory


class ElevationService:

    TILE_SIZE = 256
    AWS_ELEVATION = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"

    def __init__(self, zoom=None):
        self.zoom = zoom
        self.x = None
        self.y = None
        self._current_grid = None

    def get_grid(self, x, y):
        if x != self.x or y != self.y:
            self.x = x
            self.y = y
            img = Image.open(self._get_tile_path(self.zoom, x, y))
            grid = numpy.array(img.getdata(), dtype='float32').reshape((*reversed(img.size), 3))
            img.close()

            # decode AWS elevation to height grid
            self._current_grid = (grid[:, :, 0] * 256.0 + grid[:, :, 1] + grid[:, :, 2] / 256.0) - 32768.0
        return self._current_grid

    @staticmethod
    def _write_esri_grid_ascii_file(path, data, extent, cellsize):
        pass

    @staticmethod
    def _get_tile_path(z, x, y):
        return os.path.join(get_resources_directory(), 'Tiles', 'AWS', z, x, "{}.png".format(y))

    def get_tiles(self, extent):

        async def fetch_tile(client, url, tile_path):
            async with client.get(url) as r:
                tile_im = Image.open(BytesIO(await r.read()))
                tile_im.save(tile_path)

        # Retrieve tiles that we don't currently have
        with aiohttp.ClientSession() as client:
            requests = []
            for t in mercantile.tiles(extent.xmin, extent.ymin, extent.xmax, extent.ymax, [self.zoom]):
                z, x, y = str(t.z), str(t.x), str(t.y)
                path = self._get_tile_path(z, x, y)
                if not os.path.exists(path):
                    url = self.AWS_ELEVATION.replace("{z}", z).replace("{x}", x).replace("{y}", y)
                    requests.append(fetch_tile(client, url, path))
            asyncio.get_event_loop().run_until_complete(asyncio.gather(*requests))

    def create_dem(self, plugin, save_path):
        if plugin.data_type != DataPlugin.RASTER:
            raise ValueError("DEM generation only supported for raster based plugins.")

        if plugin.extent.projection is None:
            raise ValueError("Plugin extent has no projection info")

        native_extent = plugin.extent
        projected_extent = native_extent.projection.project(Proj(init="EPSG:4326"))
        w, s, e, n = projected_extent.xmin, projected_extent.ymin, projected_extent.xmax, projected_extent.ymax
        # ensure tiles for extent are on disk
        self.get_tiles(projected_extent)

        width, height = plugin.shape
        res = plugin.resolution
        height_grid = numpy.zeros(plugin.shape, dtype='float32')
        for j in range(height):
            for i in range(width):
                x = native_extent.xmin + i * res
                y = native_extent.ymin + j * res

                # convert x,y to wgs extent
                lon, lat = transform(native_extent.projection, projected_extent.projection, x, y)

                # determine tile and get the right grid
                tile = mercantile.tile(lon, lat, self.zoom)
                grid = self.get_grid(tile.x, tile.y)

                # determine position within grid
                p_x = numpy.floor((lon - w) / (e - w) * self.TILE_SIZE)
                p_y = numpy.floor((1 - ((lat - s) / (n - s)) * self.TILE_SIZE))
                height_grid[j][i] = grid[p_y,p_x]

        self._write_esri_grid_ascii_file(save_path, height_grid, native_extent, res)
        # Todo: create new RasterDataPlugin from
