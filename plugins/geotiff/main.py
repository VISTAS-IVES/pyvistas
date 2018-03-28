import os

import rasterio
from pyproj import Proj
import numpy as np
import numpy.ma as ma

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
    affine = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.shape = None
        self.extent = None
        self.resolution = None
        self.affine = None
        self._nodata = None
        self._count = None
        self._current_band = None
        self._current_grid = None

    def load_data(self):
        file_name = self.path.split(os.sep)[-1]
        *name, ext = file_name.split('.')
        self.data_name = '.'.join(name)

        with rasterio.open(self.path) as src:
            projection = Proj(src.crs)
            self.shape = src.shape
            self.resolution = src.res[0]
            self.affine = src.transform
            self.extent = Extent(*list(src.bounds), projection)
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
        if band == self._current_band:
            return self._current_grid.copy()
        self._current_band = band
        with rasterio.open(self.path, 'r') as src:
            self._current_grid = ma.array(src.read(band), mask=np.logical_not(src.read_masks(band)))
        return self._current_grid.copy()

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
