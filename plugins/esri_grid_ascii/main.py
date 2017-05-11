from linecache import getline
import json
import datetime
import numpy
import os
import re
from pyproj import Proj

from vistas.core.gis.extent import Extent
from vistas.core.plugins.data import RasterDataPlugin, VariableStats, TemporalInfo


class ESRIGridAscii(RasterDataPlugin):

    id = 'esri_grid_ascii'
    name = 'ESRI Grid Ascii Data Plugin'
    description = 'A plugin to read ESRI Grid Ascii (.asc) files.'
    author = 'Conservation Biology Institute'
    extensions = [('asc', 'Ascii Grid')]

    UTM_10N = "+proj=utm +zone=10 +ellps=GRS80 +datum=NAD83 +units=m +no_defs"

    # VELMA filename patterns
    VELMA_FILENAME_BASIC_RE = re.compile(r"((.+)_(\d+)_(\d+)_(\d{4})_(\d+)\.asc)", re.I)
    VELMA_FILENAME_NO_LAYER_RE = re.compile(r"((.+)_(\d+)_(\d{4})_(\d+)\.asc)", re.I)
    VELMA_FILENAME_SUBDAY_RE = re.compile(r"((.+)_(\d+)_(\d+)_(\d{4})_(\d+)_(\d+)_(\d+)\.asc)", re.I)
    VELMA_FILENAME_SUBDAY_NO_LAYER_RE = re.compile(r"((.+)_(\d+)_(\d{4})_(\d+)_(\d+)_(\d+)\.asc)", re.I)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.data = None
        self.header = {}
        self.current_grid = None
        self._extent = None
        self._temporal_info = None

    @staticmethod
    def _read_header(path):
        header = {}
        header['cols'], header['rows'], header['xllcorner'], header['yllcorner'], \
        header['cellsize'], header['nodata_value'] = [float(h.split(" ")[-1].strip())
                                        for h in [getline(path, i) for i in range(1, 7)]]
        return header

    def load_data(self):

        # Parse header
        self.header = self._read_header(self.path)

        # TODO - check for VELMA matches

        self.data = numpy.loadtxt(self.path, skiprows=6)

        self.current_grid = self.data   # Todo - only temporary to test loading, remove

        prj_file = self.path.replace('.asc', '.prj')
        if os.path.exists(prj_file):
            projection = Proj("+proj=utm +zone=10 +ellps=GRS80 +datum=NAD83 +units=m +no_defs")
            # Todo: check for PRJ file properly, and then get the pyproj definition
        else:
            projection = Proj(self.UTM_10N)

        self._extent = Extent(
            self.header['xllcorner'],
            self.header['yllcorner'],
            self.header['xllcorner'] + self.header['cellsize'] * self.header['cols'],
            self.header['yllcorner'] + self.header['cellsize'] * self.header['rows'],
            projection=projection
        )

        # Todo - build a [datetime.datetime] objects from the regex.
        self._temporal_info = TemporalInfo()

    @property
    def data_name(self):
        return self.name

    @staticmethod
    def is_valid_file(path):
        h = ESRIGridAscii._read_header(path)
        return h['rows'] > 0 and h['cols'] > 0

    def get_data(self, variable, date=None):
        # Todo - Get multiple days of data
        return self.data

    @property
    def shape(self):
        return self.current_grid.shape

    @property
    def resolution(self):
        return self.header['cellsize']

    @property
    def extent(self):
        return self._extent

    @property
    def time_info(self):
        return self._temporal_info

    @property
    def variables(self):
        return [self.name]

    def variable_stats(self, variable):
        stats_path = self.path.replace('.asc', '.json')
        if os.path.exists(stats_path):
            with open(stats_path, 'r') as f:
                return VariableStats.from_dict({**json.loads(f.read()), **self.header})
        else:
            return VariableStats(misc=self.header)

    @property
    def has_stats(self):
        return os.path.exists(self.path.replace('.asc', '.json'))

    def calculate_stats(self):
        if self.has_stats:
            return

        stats = VariableStats()
        if self.time_info and self.time_info.is_temporal:
            return  # Todo: Calculate multiple grids of data
        else:
            print('creating grid attributes!')
            grid = self.get_data("")
            stats.min_value = grid.min()
            stats.max_value = grid.max()
            stats.nodata_value = self.header['nodata_value']
            stats.misc['shape'] = "({},{})".format(*grid.shape)
        with open(self.path.replace('.asc', '.json'), 'w') as f:
            f.write(json.dumps(stats.to_dict))

    @staticmethod
    def _day_count(date):
        pass



