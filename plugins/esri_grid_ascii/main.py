from linecache import getline
import json
import datetime
import numpy
import os
import re
from bisect import insort
from pyproj import Proj

from vistas.core.timeline import Timeline
from vistas.core.gis.extent import Extent
from vistas.core.plugins.data import RasterDataPlugin, VariableStats, TemporalInfo


class ESRIGridAscii(RasterDataPlugin):

    id = 'esri_grid_ascii'
    name = 'ESRI Grid Ascii Data Plugin'
    description = 'A plugin to read ESRI Grid Ascii (.asc) files.'
    author = 'Conservation Biology Institute'
    extensions = [('asc', 'ESRI Ascii Grid')]

    UTM_10N = "+proj=utm +zone=10 +ellps=GRS80 +datum=NAD83 +units=m +no_defs"

    # VELMA filename patterns
    VELMA_FILENAME_BASIC_RE = re.compile(r"(.+)_(\d+)_(\d+)_(\d{4})_(\d+)\.asc", re.I)
    VELMA_FILENAME_NO_LAYER_RE = re.compile(r"(.+)_(\d+)_(\d{4})_(\d+)\.asc", re.I)
    VELMA_FILENAME_SUBDAY_RE = re.compile(r"(.+)_(\d+)_(\d+)_(\d{4})_(\d+)_(\d+)_(\d+)\.asc", re.I)
    VELMA_FILENAME_SUBDAY_NO_LAYER_RE = re.compile(r"(.+)_(\d+)_(\d{4})_(\d+)_(\d+)_(\d+)\.asc", re.I)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._header = {}
        self._extent = None
        self._temporal_info = None
        self._name = None
        self._has_layer = False
        self._loop = None
        self._layer = None
        self._is_subday = False
        self._is_velma = False
        self._velma_pattern = None

    @staticmethod
    def _read_header(path):
        header = dict(h.split() for h in (getline(path, i) for i in range(1, 7)))
        header = {k: float(header[k])for k in header}
        header['ncols'] = int(header['ncols'])
        header['nrows'] = int(header['nrows'])
        return header

    def load_data(self):

        # Parse header
        self._header = self._read_header(self.path)
        filename = self.path.split(os.sep)[-1]

        # Check for VELMA filename matches
        for pattern in [self.VELMA_FILENAME_BASIC_RE, self.VELMA_FILENAME_NO_LAYER_RE,
                        self.VELMA_FILENAME_SUBDAY_RE, self.VELMA_FILENAME_SUBDAY_NO_LAYER_RE]:
            match = pattern.match(filename)
            if match:
                self._velma_pattern = pattern
                self._name = match.group(1)
                self._loop = match.group(2)

                self._has_layer = pattern in [self.VELMA_FILENAME_BASIC_RE, self.VELMA_FILENAME_SUBDAY_RE]
                if self._has_layer:
                    self._layer = match.group(3)
                self._is_subday = pattern in [self.VELMA_FILENAME_SUBDAY_RE, self.VELMA_FILENAME_SUBDAY_NO_LAYER_RE]
                self._is_velma = True
                break

        prj_file = self.path.replace('.asc', '.prj')
        if os.path.exists(prj_file):
            projection = None   # Todo: check for PRJ file properly, and then get the pyproj definition
        else:
            projection = Proj(self.UTM_10N)

        self._extent = Extent(
            self._header['xllcorner'],
            self._header['yllcorner'],
            self._header['xllcorner'] + self._header['cellsize'] * self._header['ncols'],
            self._header['yllcorner'] + self._header['cellsize'] * self._header['nrows'],
            projection=projection
        )
        self._temporal_info = TemporalInfo()

        if not self._is_velma:
            self._name = self.path.split(os.sep)[-1].split('.')[0]
            return

        timestamps = []
        for f in os.listdir(os.path.dirname(os.path.abspath(self.path))):
            filename = f.split(os.sep)[-1]
            match = self._velma_pattern.match(filename)

            # Skip if match is None and if match name or loop is wrong
            if match and match.group(1) == self._name and match.group(2) == self._loop:

                # Skip if match layer is wrong, if applicable
                if self._has_layer and match.group(3) != self._layer:
                    continue

                years = int(match.group(4 if self._has_layer else 3))
                days = int(match.group(5 if self._has_layer else 4))
                hours = int(match.group(6 if self._has_layer else 5)) if self._is_subday else 0
                minutes = int(match.group(7 if self._has_layer else 6)) if self._is_subday else 0
                insort(timestamps, datetime.datetime(years, 1, 1, hours, minutes) + datetime.timedelta(days - 1))

        self._temporal_info.timestamps = timestamps

    @property
    def data_name(self):
        return self._name

    @staticmethod
    def is_valid_file(path):
        h = ESRIGridAscii._read_header(path)
        return h['nrows'] > 0 and h['ncols'] > 0

    def get_data(self, variable, date=None):
        path = os.path.abspath(self.path)
        nodata_value = self._header['nodata_value']
        if self._is_velma and self._temporal_info.is_temporal:

            if date is None:
                date = Timeline.app().current

            start = self._temporal_info.timestamps[0]
            end = self._temporal_info.timestamps[-1]

            if date < start:
                date = start
            elif date > end:
                date = end

            filename = "{}_{}".format(self._name, self._loop)
            if self._has_layer:
                filename = filename + '_{}'.format(self._layer)

            filename = filename + "_{}_{}".format(date.year, date.timetuple().tm_yday)
            if self._is_subday:
                filename = filename + '_{:2d}_{:2d}'.format(date.hour, date.minute)
            filename = "{}.asc".format(filename)
            path = os.path.join(os.path.dirname(path), filename)

        data = numpy.loadtxt(path, skiprows=6).astype(numpy.float32)
        data = numpy.ma.masked_where(data == nodata_value, data)    # Mask out nodata
        return data.T

    @property
    def shape(self):
        return self._header['nrows'], self._header['ncols']

    @property
    def resolution(self):
        return self._header['cellsize']

    @property
    def extent(self):
        return self._extent

    @property
    def time_info(self):
        return self._temporal_info

    @property
    def variables(self):
        return [self._name]

    def variable_stats(self, variable):
        stats_path = self.path.replace('.asc', '.json')
        if os.path.exists(stats_path):
            with open(stats_path, 'r') as f:
                return VariableStats.from_dict({**json.loads(f.read()), **self._header})
        else:
            return VariableStats(misc=self._header)

    @property
    def has_stats(self):
        return os.path.exists(self.path.replace('.asc', '.json'))

    def calculate_stats(self):
        if self.has_stats:
            return

        stats = VariableStats()
        if self.time_info and self.time_info.is_temporal:
            maxs = []
            mins = []
            for step in self.time_info.timestamps:
                grid = self.get_data("", step)
                mins.append(grid.min())
                maxs.append(grid.max())
            stats.min_value = float(min(mins))
            stats.max_value = float(max(maxs))
        else:
            grid = self.get_data("")
            stats.min_value = float(grid.min())
            stats.max_value = float(grid.max())

        stats.nodata_value = self._header['nodata_value']
        stats.misc['shape'] = "({},{})".format(*self.shape)
        with open(self.path.replace('.asc', '.json'), 'w') as f:
            f.write(json.dumps(stats.to_dict))
