import datetime
import os
import re
from bisect import insort

import rasterio
from osgeo.osr import SpatialReference
from pyproj import Proj

from vistas.core.gis.extent import Extent
from vistas.core.plugins.data import RasterDataPlugin, VariableStats, TemporalInfo
from vistas.core.timeline import Timeline


class ESRIGridAscii(RasterDataPlugin):

    id = 'esri_grid_ascii'
    name = 'ESRI Grid Ascii Data Plugin'
    description = 'A plugin to read ESRI Grid Ascii (.asc) files.'
    author = 'Conservation Biology Institute'
    version = '1.0'
    extensions = [('asc', 'ESRI Ascii Grid')]

    # VELMA filename patterns
    VELMA_FILENAME_BASIC_RE = re.compile(r"(.+)_(\d+)_(\d+)_(\d{4})_(\d+)\.asc", re.I)
    VELMA_FILENAME_NO_LAYER_RE = re.compile(r"(.+)_(\d+)_(\d{4})_(\d+)\.asc", re.I)
    VELMA_FILENAME_SUBDAY_RE = re.compile(r"(.+)_(\d+)_(\d+)_(\d{4})_(\d+)_(\d+)_(\d+)\.asc", re.I)
    VELMA_FILENAME_SUBDAY_NO_LAYER_RE = re.compile(r"(.+)_(\d+)_(\d{4})_(\d+)_(\d+)_(\d+)\.asc", re.I)

    affine = None
    extent = None
    shape = None
    resolution = None
    time_info = None
    data_name = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extent = None
        self.shape = None
        self.resolution = None
        self.affine = None
        self.time_info = None
        self.data_name = None
        self._nodata_value = None
        self._has_layer = False
        self._loop = None
        self._layer = None
        self._is_subday = False
        self._is_velma = False
        self._velma_pattern = None
        self._current_grid = None
        self._current_time = None
        self._current_variable = None

    def load_data(self):
        filename = self.path.split(os.sep)[-1]

        # Check for VELMA filename matches
        for pattern in [self.VELMA_FILENAME_BASIC_RE, self.VELMA_FILENAME_NO_LAYER_RE,
                        self.VELMA_FILENAME_SUBDAY_RE, self.VELMA_FILENAME_SUBDAY_NO_LAYER_RE]:
            match = pattern.match(filename)
            if match:
                self._velma_pattern = pattern
                self.data_name = match.group(1)
                self._loop = match.group(2)

                self._has_layer = pattern in [self.VELMA_FILENAME_BASIC_RE, self.VELMA_FILENAME_SUBDAY_RE]
                if self._has_layer:
                    self._layer = match.group(3)
                self._is_subday = pattern in [self.VELMA_FILENAME_SUBDAY_RE, self.VELMA_FILENAME_SUBDAY_NO_LAYER_RE]
                self._is_velma = True
                break

        projection = None
        prj_file = self.path.replace('.asc', '.prj')
        if os.path.exists(prj_file):
            with open(prj_file, 'r') as f:
                ref = SpatialReference()
                ref.ImportFromWkt(f.read())
                projection = Proj(ref.ExportToProj4())

        # Capture georeference
        with rasterio.open(self.path) as src:
            self.affine = src.transform
            self.shape = src.shape
            self.resolution = src.res[0]    # Assumed to be square
            self.extent = Extent(*list(src.bounds), projection=projection)
            self._nodata_value = src.nodata

        self.time_info = TemporalInfo()
        if not self._is_velma:
            self.data_name = self.path.split(os.sep)[-1].split('.')[0]
            return

        timestamps = []
        for f in os.listdir(os.path.dirname(os.path.abspath(self.path))):
            filename = f.split(os.sep)[-1]
            match = self._velma_pattern.match(filename)

            # Skip if match is None and if match name or loop is wrong
            if match and match.group(1) == self.data_name and match.group(2) == self._loop:

                # Skip if match layer is wrong, if applicable
                if self._has_layer and match.group(3) != self._layer:
                    continue

                years = int(match.group(4 if self._has_layer else 3))
                days = int(match.group(5 if self._has_layer else 4))
                hours = int(match.group(6 if self._has_layer else 5)) if self._is_subday else 0
                minutes = int(match.group(7 if self._has_layer else 6)) if self._is_subday else 0
                insort(timestamps, datetime.datetime(years, 1, 1, hours, minutes) + datetime.timedelta(days - 1))

        self.time_info.timestamps = timestamps

    @staticmethod
    def is_valid_file(path):
        try:
            with rasterio.open(path, 'r') as src:
                return src.bounds is not None
        except rasterio.RasterioIOError:
            return False

    def get_data(self, variable, date=None):
        if self._current_grid is not None and self._current_time == date and self._current_variable == variable:
            return self._current_grid.copy()

        path = os.path.abspath(self.path)
        if self._is_velma and self.time_info.is_temporal:
            if date is None:
                date = Timeline.app().current

            start = self.time_info.timestamps[0]
            end = self.time_info.timestamps[-1]
            if date < start:
                date = start
            elif date > end:
                date = end

            filename = "{}_{}".format(self.data_name, self._loop)
            if self._has_layer:
                filename = filename + '_{}'.format(self._layer)
            filename = filename + "_{}_{}".format(date.year, date.timetuple().tm_yday)
            if self._is_subday:
                filename = filename + '_{:2d}_{:2d}'.format(date.hour, date.minute)
            filename = "{}.asc".format(filename)
            path = os.path.join(os.path.dirname(path), filename)

        with rasterio.open(path) as src:
            self._current_grid = src.read(1)
        self._current_variable = variable
        self._current_time = date
        return self._current_grid.copy()

    @property
    def variables(self):
        return [self.data_name]

    def calculate_stats(self):
        if self.stats.is_stale:
            stats = VariableStats()
            maxs = []
            mins = []
            steps = self.time_info.timestamps if self.time_info.is_temporal else [0]
            for step in steps:
                grid = self.get_data("", step)
                mins.append(grid[grid != self._nodata_value].min())
                maxs.append(grid[grid != self._nodata_value].max())
            stats.min_value = float(min(mins))
            stats.max_value = float(max(maxs))
            stats.nodata_value = self._nodata_value
            stats.misc['shape'] = "({},{})".format(*self.shape)
            self.stats[self.data_name] = stats
            self.save_stats()
