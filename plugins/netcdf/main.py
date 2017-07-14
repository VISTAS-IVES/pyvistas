import os
import datetime
import numpy
from vistas.core.plugins.data import RasterDataPlugin, TemporalInfo, VariableStats
from vistas.core.gis.extent import Extent
from netCDF4 import Dataset


class NetCDF4DataPlugin(RasterDataPlugin):

    id = 'netcdf'
    name = 'NetCDF'
    description = 'A plugin to read NetCDF (.nc) files.'
    author = 'Conservation Biology Institute'
    version = '1.0'
    extensions = [('nc', 'NetCDF')]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._header = {}
        self._temporal_info = None
        self._stats = {}
        self._name = None
        self._extent = None
        self._variables = []

        # NetCDF-specific variables
        self.x_dim = None
        self.y_dim = None
        self.t_dim = None
        self.y_increasing = False
        self.x_length = None
        self.y_length = None
        self.x_cellsize = None
        self.y_cellsize = None

    def load_data(self):

        self._name = self.path.split(os.sep)[-1].split('.')[0]
        with Dataset(self.path, 'r') as ds:
            dimensions = list(ds.dimensions.keys())
            self._variables = [var for var in ds.variables if var not in dimensions]

            if 'x' in dimensions:
                self.x_dim, self.y_dim = 'x', 'y'
            elif 'lon' in dimensions:
                self.x_dim, self.y_dim = 'lon', 'lat'
            elif 'longitude' in dimensions:
                self.x_dim, self.y_dim = 'longitude', 'latitude'
            else:
                raise KeyError("NetCDF file doesn't have recognizable dimension names (x, lat, latitude, etc.)")

            if 'time' in dimensions:
                self.t_dim = 'time'

                if 'time' not in ds.variables:  # No actual timestamps, make generic timestamps
                    start_date = datetime.datetime(1970, 1, 1)
                    self._temporal_info = TemporalInfo()
                    self._temporal_info.timestamps = [start_date + datetime.timedelta(days=365 * i)
                                                      for i in range(ds.dimensions['time'].size)]

                else:
                    pass    # What if 'time' is in the variables?

            # Determine spatial extent
            x_values = ds.variables[self.x_dim][:]
            y_values = ds.variables[self.y_dim][:]
            xmin = x_values[0]
            xmax = x_values[-1]
            ymin = y_values[0]
            ymax = y_values[-1]
            self.y_increasing = ymax < ymin
            if self.y_increasing:
                ymax, ymin = ymin, ymax

            self.x_length = x_values.size
            self.y_length = y_values.size
            self.x_cellsize = x_values[1] - x_values[0]
            self.y_cellsize = y_values[0] - y_values[1] if self.y_increasing else y_values[1] - y_values[0]

            self._extent = Extent(xmin - self.x_cellsize / 2,
                                  xmax + self.x_cellsize / 2,
                                  ymin - self.y_cellsize / 2,
                                  ymax + self.y_cellsize / 2)    # Todo - projection info?

    @staticmethod
    def is_valid_file(path):
        with Dataset(path, 'r') as ds:
            if len(ds.variables.keys()) > 0:
                return True
        return False

    @property
    def data_name(self):
        return self._name

    def get_data(self, variable, date=None):
        with Dataset(self.path, 'r') as ds:
            data = ds.variables[variable][:][self._temporal_info.timestamps.index(date)]
            if isinstance(data, numpy.ma.MaskedArray):
                data = data.data
        return data.T

    @property
    def shape(self):
        with Dataset(self.path, 'r') as ds:
                return ds.variables[self._variables[0]].shape   # Shape assumed to be uniform across variables

    @property
    def extent(self):
        return self._extent

    @property
    def resolution(self):
        return (self._extent.xmax - self._extent.xmin) / self.x_length

    @property
    def time_info(self):
        return self._temporal_info

    @property
    def variables(self):
        return self._variables

    def variable_stats(self, variable):
        return self._stats[variable]

    def calculate_stats(self):
        self._stats = {}
        with Dataset(self.path, 'r') as ds:
            for var in self._variables:
                data = ds.variables[var][:]
                self._stats[var] = VariableStats(
                    min_value=data.min(),
                    max_value=data.max(),
                    nodata_value=ds.variables[var]._FillValue if isinstance(data, numpy.ma.MaskedArray) else None
                )
