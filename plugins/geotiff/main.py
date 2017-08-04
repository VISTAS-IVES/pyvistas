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
    extensions = [('tif', 'GeoTIFF')]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._name = None
        self._shape = None
        self._extent = None
        self._resolution = None
        self._nodata = None
        self._count = None

    def load_data(self):
        self._name = self.path.split(os.sep)[-1].split('.tif')[0]
        with rasterio.open(self.path) as src:
            projection = Proj(src.crs)
            self._shape = src.shape
            self._resolution = src.res[0]
            xmin, ymin = src.xy(src.height, 0, 'ul')
            xmax, ymax = src.xy(0, src.width, 'ul')
            self._extent = Extent(xmin, ymin, xmax, ymax, projection)
            self._nodata = src.nodata
            self._count = src.count

    @property
    def data_name(self):
        return self._name

    @staticmethod
    def is_valid_file(path):
        return True

    def get_data(self, variable, date=None):
        band = int(variable.split(' ')[-1])
        with rasterio.open(self.path, 'r') as src:
            return src.read(band).T

    @property
    def shape(self):
        return self._shape

    @property
    def resolution(self):
        return self._resolution

    @property
    def extent(self):
        return self._extent

    @property
    def variables(self):
        return ['Band {}'.format(i) for i in range(1, self._count + 1)]

    def variable_stats(self, variable):
        band = variable.split(' ')[-1]
        stats_path = self.path.replace('.tif', '.json')
        if os.path.exists(stats_path):
            with open(stats_path, 'r') as f:
                all_stats = json.load(f)
                return VariableStats.from_dict(all_stats[band])
        else:
            return VariableStats()

    @property
    def has_stats(self):
        return os.path.exists(self.path.replace('.tif', '.json'))

    def calculate_stats(self):
        if self.has_stats:
            return

        all_stats = {}
        with rasterio.open(self.path) as src:
            for band in range(1, self._count + 1):
                data = src.read(band)
                masked_data = data[data != self._nodata]
                stats = VariableStats(float(masked_data.min()), float(masked_data.max()), self._nodata)
                all_stats[band] = stats.to_dict
        with open(self.path.replace('.tif', '.json'), 'w') as f:
            json.dump(all_stats, f)
