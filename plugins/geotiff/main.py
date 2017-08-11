import json
import os

import rasterio
from pyproj import Proj

from vistas.core.gis.extent import Extent
from vistas.core.plugins.data import RasterDataPlugin, VariableStats


class GeoTIFF(RasterDataPlugin):

    id = 'geotiff'
    name = 'GeoTIFF Data Plugin'
    description = 'Reads GeoTIFF (.tif) files'
    author = 'Conservation Biology Institute'
    version = '1.0'
    extensions = [('tif', 'GeoTIFF'), ('tiff', 'GeoTIFF')]

    data_name = None
    shape = None
    resolution = None
    extent = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.shape = None
        self.extent = None
        self.resolution = None
        self._nodata = None
        self._count = None
        self._stats_path = None

    def load_data(self):
        file_name = self.path.split(os.sep)[-1]
        *name, ext = file_name.split('.')
        self.data_name = '.'.join(name)
        self._stats_path = os.path.join(os.path.dirname(self.path), '{}.{}'.format(self.data_name, 'json'))

        with rasterio.open(self.path) as src:
            projection = Proj(src.crs)
            self.shape = src.shape
            self.resolution = src.res[0]
            xmin, ymin = src.xy(src.height, 0, 'ul')
            xmax, ymax = src.xy(0, src.width, 'ul')
            self.extent = Extent(xmin, ymin, xmax, ymax, projection)
            self._nodata = src.nodata
            self._count = src.count

    @staticmethod
    def _band(b):
        return b.split(' ')[-1]

    @staticmethod
    def is_valid_file(path):
        return True

    def get_data(self, variable, date=None):
        band = int(self._band(variable))
        with rasterio.open(self.path, 'r') as src:
            return src.read(band)

    @property
    def variables(self):
        return ['Band {}'.format(i) for i in range(1, self._count + 1)]

    def calculate_stats(self):
        if self.stats.is_stale:
            with rasterio.open(self.path) as src:
                variables = self.variables
                for i, band in enumerate(range(1, self._count + 1)):
                    data = src.read(band)
                    if self._nodata is not None:
                        data = data[data != self._nodata]
                    self.stats[variables[i]] = VariableStats(float(data.min()), float(data.max()), self._nodata)
            self.save_stats()
