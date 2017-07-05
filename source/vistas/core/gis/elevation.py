import mercantile
import aiohttp
import asyncio
import os
import numpy
from PIL import Image
from pyproj import Proj, transform
from io import BytesIO
from vistas.core.plugins.interface import Plugin
from vistas.core.plugins.data import RasterDataPlugin
from vistas.core.paths import get_resources_directory


class ElevationService:

    TILE_SIZE = 256
    AWS_ELEVATION = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"

    def __init__(self, zoom=15):
        self.zoom = zoom
        self.x = None
        self.y = None
        self._current_grid = None

    def get_grid(self, x, y):
        if x != self.x or y != self.y:
            self.x = x
            self.y = y
            img = Image.open(self._get_tile_path(self.zoom, x, y))
            grid = numpy.array(img.getdata(), dtype=numpy.float32).reshape(256, 256, 3)
            img.close()

            # decode AWS elevation to height grid
            self._current_grid = (grid[:, :, 0] * 256.0 + grid[:, :, 1] + grid[:, :, 2] / 256.0) - 32768.0
        return self._current_grid

    @staticmethod
    def _write_esri_grid_ascii_file(path, data, extent, cellsize):
        xllcorner, yllcorner, *_ = extent.as_list()
        nrows, ncols = data.shape

        header = '\n'.join(['{} {}'.format(key, val) for key, val in {
            'nrows': nrows,
            'ncols': ncols,
            'xllcorner': xllcorner,
            'yllcorner': yllcorner,
            'cellsize': cellsize,
            'nodata_value': -9999.0
        }.items()])

        numpy.savetxt(path, data, header=header, comments='')

    @staticmethod
    def _get_tile_path(z, x, y):
        return os.path.join(get_resources_directory(), 'Tiles', 'AWS', str(z), str(x), "{}.png".format(y))

    def get_tiles(self, extent):

        async def fetch_tile(client, url, tile_path):
            async with client.get(url) as r:
                tile_im = Image.open(BytesIO(await r.read()))
                if not os.path.exists(os.path.dirname(tile_path)):
                    os.makedirs(os.path.dirname(tile_path))
                tile_im.save(tile_path)

        # Retrieve tiles that we don't currently have
        with aiohttp.ClientSession() as client:
            requests = []
            min_x, min_y, max_x, max_y = [None] * 4
            for t in mercantile.tiles(extent.xmin, extent.ymin, extent.xmax, extent.ymax, [self.zoom]):
                z, x, y = t.z, t.x, t.y
                if min_x is None:
                    min_x = max_x = x
                    min_y = max_y = y
                else:
                    min_x = x if x < min_x else min_x
                    min_y = y if y < min_y else min_y
                    max_x = x if x > max_x else max_x
                    max_y = y if y > max_y else max_y

                path = self._get_tile_path(z, x, y)
                if not os.path.exists(path):
                    url = self.AWS_ELEVATION.format(z=z, x=x, y=y)
                    requests.append(fetch_tile(client, url, path))

            # Get corner tiles for good measure
            min_x -= 1
            min_y -= 1
            max_x += 1
            max_y += 1

            for i in range(min_x, max_x+1):

                # Top tiles
                if not os.path.exists(self._get_tile_path(self.zoom, i, min_y)):
                    requests.append(
                        fetch_tile(client, self.AWS_ELEVATION.format(
                            z=self.zoom, x=i, y=min_y
                        ), self._get_tile_path(self.zoom, i, min_y))
                    )

                # Bottom tiles
                if not os.path.exists(self._get_tile_path(self.zoom, i, max_y)):
                    requests.append(    # Bottom tiles
                        fetch_tile(client, self.AWS_ELEVATION.format(
                            z=self.zoom, x=i, y=max_y
                        ), self._get_tile_path(self.zoom, i, max_y))
                    )

                if i == min_x or i == max_x:    # Side tiles
                    for j in range(min_y+1, max_y):
                        if not os.path.exists(self._get_tile_path(self.zoom, i, j)):
                            requests.append(
                                fetch_tile(client, self.AWS_ELEVATION.format(
                                    z=self.zoom, x=i, y=j
                                ), self._get_tile_path(self.zoom, i, j))
                            )

            asyncio.get_event_loop().run_until_complete(asyncio.gather(*requests))

    def create_dem(self, plugin, save_path, task):
        if not isinstance(plugin, RasterDataPlugin):
            raise ValueError("DEM generation only supported for raster-based plugins.")

        if plugin.extent.projection is None:
            raise ValueError("Plugin extent has no projection info")

        native_extent = plugin.extent
        projected_extent = native_extent.project(Proj(init="EPSG:4326"))

        # Ensure tiles for extent are on disk
        task.status = task.RUNNING
        task.description = 'Building DEM file, saving to {}'.format(save_path)
        self.get_tiles(projected_extent)

        height, width = plugin.shape
        task.target = width * height
        res = plugin.resolution
        height_grid = numpy.zeros(plugin.shape, dtype=numpy.float32)
        for j in range(height):
            for i in range(width):
                x = native_extent.xmin + i * res
                y = native_extent.ymax - j * res

                # convert x,y to wgs extent
                lon, lat = transform(native_extent.projection, projected_extent.projection, x, y)

                # determine tile and get the right grid
                tile = mercantile.tile(lon, lat, self.zoom)
                bounds = mercantile.bounds(tile)

                # determine position within grid
                p_x = (lon - bounds.west) / (bounds.east - bounds.west)
                p_y = (1 - ((lat - bounds.south) / (bounds.north - bounds.south)))

                if p_y < 0.0:
                    p_y += 1.0
                    y -= 1
                elif p_y >= 1.0:
                    p_y -= 1.0
                    y += 1

                u = int(numpy.floor(p_x * self.TILE_SIZE))
                v = int(numpy.floor(p_y * self.TILE_SIZE))

                height_grid[j][i] = self.get_grid(tile.x, tile.y)[v, u]
                task.inc_progress()

        self._write_esri_grid_ascii_file(save_path, height_grid, native_extent, res)

        plugin = Plugin.by_name('esri_grid_ascii')()
        plugin.set_path(save_path)
        return plugin
