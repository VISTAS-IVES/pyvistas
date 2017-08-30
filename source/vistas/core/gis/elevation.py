import asyncio
import os
from io import BytesIO
from typing import Dict, Union

import aiohttp
import mercantile
import numpy
from PIL import Image
from pyproj import Proj, transform

from vistas.core.gis.file_writer import RasterWriter
from vistas.core.paths import get_config_dir
from vistas.core.plugins.data import FeatureDataPlugin
from vistas.core.plugins.interface import Plugin

TILE_SIZE = 256                 # Our tile representation size, can be changed
DEFAULT_TILE_SIZE = 256         # ZXY tiles


def meters_per_px(zoom):
    return 6378137.0 * 2 * numpy.pi / (TILE_SIZE * (2 ** zoom))


class ElevationService:
    """
    An interface for obtaining elevation data from public datasets sorted as a tile service. Can generate a digital
    elevation model (DEM) for use in visualizing spatial datasets in 3D.
    """

    TILE_SIZE = 256
    AWS_ELEVATION = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
    AWS_NORMALS = "https://s3.amazonaws.com/elevation-tiles-prod/normal/{z}/{x}/{y}.png"

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
            if self.resolution > meters_per_px(i):
                self._zoom = i - 1 if i != 0 else 0
                return self._zoom

        # Alas, we couldn't calculate a proper zoom, default to max zoom
        self._zoom = 15
        return self._zoom

    @zoom.setter
    def zoom(self, zoom):
        self._zoom = int(zoom)

    def get_grid(self, x, y, z=None, src=AWS_ELEVATION):
        z = z if z else self.zoom
        if x != self.x or y != self.y or src != self.AWS_ELEVATION:
            self.x = x
            self.y = y
            img = Image.open(self._get_tile_path(z, x, y, src=src))
            grid = numpy.array(img.getdata(), dtype=numpy.float32).reshape(256, 256, 3 if src == self.AWS_ELEVATION else 4)
            img.close()

            # decode AWS elevation to height grid
            if src == self.AWS_ELEVATION:
                self._current_grid = (grid[:, :, 0] * 256.0 + grid[:, :, 1] + grid[:, :, 2] / 256.0) - 32768.0
            else:
                self._current_grid = grid[:, :, 0:3] / 256.0
        return self._current_grid

    @staticmethod
    def _get_tile_path(z, x, y, src=AWS_ELEVATION):
        if src == ElevationService.AWS_ELEVATION:
            datatype = 'Elevation'
        else:
            datatype = 'Normals'
        return os.path.join(get_config_dir(), 'Tiles', 'AWS', datatype, str(z), str(x), "{}.png".format(y))

    def get_tiles(self, extent, task=None):
        async def fetch_tile(client, url, tile_path):
            async with client.get(url) as r:
                tile_im = Image.open(BytesIO(await r.read()))

                if not os.path.exists(tile_path):
                    if not os.path.exists(os.path.dirname(tile_path)):
                        os.makedirs(os.path.dirname(tile_path))
                    tile_im.save(tile_path)
                if task:
                    task.inc_progress()

        loop = asyncio.get_event_loop()

        # Retrieve tiles that we don't currently have
        with aiohttp.ClientSession(loop=loop) as client:
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
                npath = self._get_tile_path(z, x, y, self.AWS_NORMALS)
                if not os.path.exists(path):
                    url = self.AWS_ELEVATION.format(z=z, x=x, y=y)
                    nurl = self.AWS_NORMALS.format(z=z, x=x, y=y)
                    requests.append(fetch_tile(client, url, path))
                    requests.append(fetch_tile(client, nurl, npath))

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

            loop.run_until_complete(asyncio.gather(*requests))

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

                u = int(numpy.floor(p_x * DEFAULT_TILE_SIZE))
                v = int(numpy.floor(p_y * DEFAULT_TILE_SIZE))

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
            # Todo - res assumes resolution is in meters. ElevationService will fail if resolution is lat/lon
            # Todo - Check for geographic projection and convert lat/lon to meters_per_px
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

    def create_data_dem(self, extent, zoom, merge=False, src=AWS_ELEVATION) -> Union[Dict[mercantile.Tile, numpy.ndarray], numpy.ndarray]:
        """
        Creates an elevation grid from elevation data in memory.
        :param extent Extent to build the DEM for.
        :param zoom The zoom level to render the DEM at.
        :param merge Indicate whether to return the DEM as a single numpy grid, or as a cache, using mercantile.Tile
        objects to index into the cache.
        :return {mercantile.Tile: numpy.ndarray} if merge==False, numpy.ndarray if merge==True
        """

        self._zoom = zoom
        wgs84 = extent.project(Proj(init='EPSG:4326'))
        self.get_tiles(wgs84)
        tiles = extent.tiles(self.zoom)
        if merge:
            ul = tiles[0]
            br = tiles[-1]
            shape = ((br.y - ul.y + 1) * DEFAULT_TILE_SIZE, (br.x - ul.x + 1) * DEFAULT_TILE_SIZE)
            if src == self.AWS_ELEVATION:
                data = numpy.zeros(shape, dtype=numpy.float32)
            else:
                data = numpy.zeros((*shape, 3), dtype=numpy.float32)
            for tile in tiles:
                w = (tile.x - ul.x) * DEFAULT_TILE_SIZE
                h = (tile.y - ul.y) * DEFAULT_TILE_SIZE
                data[h: h + DEFAULT_TILE_SIZE, w: w + DEFAULT_TILE_SIZE] = self.get_grid(tile.x, tile.y, src=src)
            return data
        else:
            return {t: self.get_grid(t.x, t.y) for t in tiles}
