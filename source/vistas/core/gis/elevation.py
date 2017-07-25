import asyncio
import os
from io import BytesIO

import aiohttp
import mercantile
import numpy
from PIL import Image
from pyproj import Proj, transform

from vistas.core.gis.extent import Extent
from vistas.core.gis.file_writer import RasterWriter
from vistas.core.paths import get_userconfig_path
from vistas.core.plugins.data import FeatureDataPlugin
from vistas.core.plugins.interface import Plugin
from vistas.core.utils import asyncio_guard


class ElevationService:
    """
    An interface for obtaining elevation data from public datasets sorted as a tile service. Can generate a digital
    elevation model (DEM) for use in visualizing spatial datasets in 3D.
    """

    TILE_SIZE = 256
    AWS_ELEVATION = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"

    def __init__(self):
        self.x = None
        self.y = None
        self.resolution = None
        self._current_grid = None
        self._zoom = None

    @property
    def zoom(self):
        """
            Only get tiles where we benefit from lower zoom level.
            See https://gist.github.com/tucotuco/1193577#file-globalmaptiles-py-L268
        """

        if self._zoom is not None:
            return self._zoom

        if self.resolution is None:
            return 15   # Max zoom for AWS

        # Calculate self._zoom once and cache
        for i in range(16):
            if self.resolution > (2 * numpy.pi * 6378137) / (256 * 2 ** i):
                self._zoom = i - 1 if i != 0 else 0
                return self._zoom

        # Alas, we couldn't calculate a proper zoom, default to max zoom
        self._zoom = 15
        return self._zoom

    @zoom.setter
    def zoom(self, zoom):
        self._zoom = int(zoom)

    def get_grid(self, x, y, z=None):
        z = z if z else self.zoom
        if x != self.x or y != self.y:
            self.x = x
            self.y = y
            img = Image.open(self._get_tile_path(z, x, y))
            grid = numpy.array(img.getdata(), dtype=numpy.float32).reshape(256, 256, 3)
            img.close()

            # decode AWS elevation to height grid
            self._current_grid = (grid[:, :, 0] * 256.0 + grid[:, :, 1] + grid[:, :, 2] / 256.0) - 32768.0
        return self._current_grid

    @staticmethod
    def _get_tile_path(z, x, y):
        return os.path.join(get_userconfig_path(), 'Tiles', 'AWS', str(z), str(x), "{}.png".format(y))

    @asyncio_guard
    def get_tiles(self, extent, task=None):
        async def fetch_tile(client, url, tile_path):
            async with client.get(url) as r:
                tile_im = Image.open(BytesIO(await r.read()))
                if not os.path.exists(os.path.dirname(tile_path)):
                    os.makedirs(os.path.dirname(tile_path))
                tile_im.save(tile_path)
                if task:
                    task.inc_progress()

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
            if task:
                task.target = len(requests)
            asyncio.get_event_loop().run_until_complete(asyncio.gather(*requests))

    def create_dem(self, native_extent, projected_extent, shape, resolution, save_path, task):

        self.resolution = resolution    # self.zoom is now available

        # Ensure tiles for extent are on disk
        task.status = task.RUNNING
        task.description = 'Collecting elevation data...'
        self.get_tiles(projected_extent, task)

        task.description = 'Building DEM file...'
        height, width = shape
        task.target = width * height
        height_grid = numpy.zeros(shape, dtype=numpy.float32)
        for j in range(height):
            for i in range(width):
                x = native_extent.xmin + i * resolution
                y = native_extent.ymax - j * resolution

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

        RasterWriter.write_esri_grid_ascii_file(save_path, height_grid, native_extent, resolution)

    def create_dem_from_plugin(self, plugin, save_path, task):
        if isinstance(plugin, FeatureDataPlugin):

            # Generate a 'wide' area for the vector data to be clipped to.
            wgs84 = plugin.extent.project(Proj(init='EPSG:4326'))
            xmin, ymin, xmax, ymax = wgs84.as_list()
            res = 300

            def measure(lat1, lon1, lat2, lon2):
                r = 6378137
                dlat = lat2 * numpy.pi / 180 - lat1 * numpy.pi / 180
                dlon = lon2 * numpy.pi / 180 - lon1 * numpy.pi / 180
                a = numpy.sin(dlat / 2) * numpy.sin(dlat / 2) \
                    + numpy.cos(lat1 * numpy.pi / 180) * numpy.cos(lat2 * numpy.pi / 180) \
                    * numpy.sin(dlon / 2) * numpy.sin(dlon / 2)
                c = 2 * numpy.arctan2(numpy.sqrt(a), numpy.sqrt(1 - a))
                return r * c

            shape = (int(measure(ymin, xmin, ymax, xmin) / res), int(measure(ymin, xmin, ymin, xmax) / res))

        else:
            shape = plugin.shape
            res = plugin.resolution

        self.create_dem(
            plugin.extent,
            plugin.extent.project(Proj(init="EPSG:4326")),
            shape, res, save_path, task
        )

        new_plugin = Plugin.by_name('esri_grid_ascii')()
        new_plugin.set_path(save_path)
        task.description = 'Calculating stats for DEM'
        task.status = task.INDETERMINATE
        new_plugin.calculate_stats()
        return new_plugin

    def create_data_dem(self, extent, zoom, merge=False):

        self._zoom = zoom
        wgs84 = extent.project(Proj(init='EPSG:4326'))
        self.get_tiles(wgs84)
        xmin, ymin, xmax, ymax = wgs84.as_list()
        ll_tile = mercantile.tile(xmin, ymin, self.zoom)
        ur_tile = mercantile.tile(xmax, ymax, self.zoom)
        ll_bbox = mercantile.bounds(ll_tile)
        ur_bbox = mercantile.bounds(ur_tile)
        xmin, ymin = ll_bbox.west, ll_bbox.south
        xmax, ymax = ur_bbox.east, ur_bbox.north
        dem_extent = Extent(xmin, ymin, xmax, ymax, projection=Proj(init='EPSG:4326'))
        tiles = extent.tiles(self.zoom)
        if merge:
            shape = ((ll_tile.y - ur_tile.y + 1) * 256, (ur_tile.x - ll_tile.x + 1) * 256)
            data = numpy.zeros(shape, dtype=numpy.float32)
            for tile in tiles:
                w = (tile.x - ll_tile.x) * 256
                h = (tile.y - ur_tile.y) * 256
                data[h: h + 256, w: w + 256] = self.get_grid(tile.x, tile.y)
            return data, dem_extent
        else:
            return (self.get_grid(t.x, t.y) for t in tiles), dem_extent
