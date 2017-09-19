import datetime
import os

from clover.netcdf.utilities import get_fill_value_for_variable
from clover.netcdf.variable import SpatialCoordinateVariable, SpatialCoordinateVariables, BoundsCoordinateVariable
from netCDF4 import Dataset

from vistas.core.gis.extent import Extent
from vistas.core.plugins.data import RasterDataPlugin, TemporalInfo, VariableStats
from vistas.core.timeline import Timeline


class NetCDF4DataPlugin(RasterDataPlugin):

    id = 'netcdf'
    name = 'NetCDF'
    description = 'A plugin to read NetCDF (.nc) files.'
    author = 'Conservation Biology Institute'
    version = '1.0'
    extensions = [('nc', 'NetCDF')]

    extent = None
    time_info = None
    variables = None
    data_name = None
    affine = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.time_info = None
        self.data_name = None
        self.extent = None
        self.variables = []

        # NetCDF-specific variables
        self.x_dim = None
        self.y_dim = None
        self.t_dim = None
        self.y_increasing = False
        self.x = None
        self.y = None
        self.x_length = None
        self.y_length = None
        self.affine = None

        # Grid caching
        self._current_variable = None
        self._current_grid = None

    def load_data(self):

        self.data_name = self.path.split(os.sep)[-1].split('.')[0]
        with Dataset(self.path, 'r') as ds:
            dimensions = list(ds.dimensions.keys())
            self.variables = [var for var in ds.variables if var not in dimensions]

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
                    self.time_info = TemporalInfo()
                    self.time_info.timestamps = [start_date + datetime.timedelta(days=365 * i)
                                                      for i in range(ds.dimensions['time'].size)]

                else:
                    pass    # What if 'time' is in the variables?

            # Determine spatial extent
            self.x = SpatialCoordinateVariable(ds.variables[self.x_dim])
            self.y = SpatialCoordinateVariable(ds.variables[self.y_dim])
            xmin = self.x.values[0]
            xmax = self.x.values[-1]
            ymin = self.y.values[0]
            ymax = self.y.values[-1]
            self.y_increasing = ymax < ymin
            if self.y_increasing:
                ymax, ymin = ymin, ymax

            self.extent = Extent(xmin - self.x.pixel_size / 2,
                                 ymin - self.x.pixel_size / 2,
                                 xmax + self.y.pixel_size / 2,
                                 ymax + self.y.pixel_size / 2)    # Todo - projection info?
            self.affine = SpatialCoordinateVariables(self.x, self.y, None).affine

    @staticmethod
    def is_valid_file(path):
        with Dataset(path, 'r') as ds:
            if len(ds.variables.keys()) > 0:
                return True
        return False

    def get_data(self, variable, date=None):
        if date is None:
            date = Timeline.app().current

        if not (variable == self._current_variable):
            with Dataset(self.path, 'r') as ds:
                self._current_grid = BoundsCoordinateVariable(ds.variables[variable])
            self._current_variable = variable

        return self._current_grid.values[self.time_info.timestamps.index(date)]

    @property
    def shape(self):
        with Dataset(self.path, 'r') as ds:
            return ds.variables[self.variables[0]].shape   # Shape assumed to be uniform across variables

    @property
    def resolution(self):
        return self.x.pixel_size

    def calculate_stats(self):
        with Dataset(self.path, 'r') as ds:
            for var in self.variables:
                variable = ds.variables[var]
                data = BoundsCoordinateVariable(variable)
                self.stats[var] = VariableStats(
                    data.values.min(), data.values.max(), get_fill_value_for_variable(variable)
                )
