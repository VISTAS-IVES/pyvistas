import datetime
import os

from clover.netcdf.utilities import get_fill_value_for_variable
from clover.netcdf.variable import SpatialCoordinateVariable, SpatialCoordinateVariables, DateVariable
import clover.netcdf.describe
from netCDF4 import Dataset
import datetime as dt
import wx

from vistas.core.gis.extent import Extent
from vistas.core.plugins.data import RasterDataPlugin, TemporalInfo, VariableStats
from vistas.core.timeline import Timeline
from vistas.ui.app import App


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
        self._resolution = None

        # Grid caching
        self._current_variable = None
        self._current_grid = None
        self.var_shape = None

    def load_data(self):
        self.data_name = self.path.split(os.sep)[-1].split('.')[0]
        with Dataset(self.path, 'r') as ds:
            # This should be: self.variables = clover.netcdf.utilities.data_variables(ds)
            # but unfortunately clover's data_variables() method is broken under python3
            # currently this may cause problems with grid_mapping or *_bnds variables
            dimensions = list(ds.dimensions.keys())
            self.variables = [var for var in ds.variables if var not in dimensions]

            recognized_dims = {'x': 'y', 'lon': 'lat', 'longitude': 'latitude'}
            for x, y in recognized_dims.items():
                if x in dimensions:
                    self.x_dim, self.y_dim = x, y
                    break
            if self.x_dim is None:
                raise KeyError("NetCDF file doesn't have recognizable dimension names (x, lat, latitude, etc.)")

            # we need a time_info attribute even if there's no time info
            self.time_info = TemporalInfo()
            recognized_time_dims = ['time', 'year', 'month', 'date']
            for timedim in recognized_time_dims:
                if timedim in dimensions:
                    self.t_dim = timedim
                    if timedim in ds.variables:
                        timevar = DateVariable(ds.variables[timedim])
                        self.time_info.timestamps = timevar.datetimes.tolist()
                        # we don't want timezones, but sometimes clover adds them
                        if self.time_info.timestamps[0].tzinfo is not None:
                            self.time_info.timestamps = [d.replace(tzinfo=None) for d in self.time_info.timestamps]
                    else: # no time variable
                        wx.MessageDialog(App.get().app_controller.main_window,
                            caption='Missing Time Data',
                            message=('{} has a time dimension "{}" but no corresponding coordinate ' +
                            'variable. Using only final timestep.').format(self.data_name, timedim), style=wx.OK).ShowModal()
                    break

            # Determine spatial extent; if multiple vars, they must all have the same extent
            self.x = SpatialCoordinateVariable(ds.variables[self.x_dim])
            self.y = SpatialCoordinateVariable(ds.variables[self.y_dim])
            self.y_increasing = self.y.values[0] < self.y.values[-1]
            grid = clover.netcdf.describe.describe(ds)['variables'][self.variables[0]]['spatial_grid']
            ext = grid['extent']
            self.extent = Extent(*[ext[d] for d in ['xmin', 'ymin', 'xmax', 'ymax']])
            self._resolution = grid['x_resolution']
            self.affine = SpatialCoordinateVariables(self.x, self.y, None).affine
            self.var_shape = ds.variables[self.variables[0]].shape
            # if a var has a temporal dimension but no temporal data, we treat it as non-temporal:
            if not self.time_info.is_temporal and len(self.var_shape) == 3:
                self.var_shape = self.var_shape[1:]

    @staticmethod
    def is_valid_file(path):
        try:
            with Dataset(path, 'r') as ds:
                if len(ds.variables.keys()) > 0:
                    return True
            return False
        except:
            return False

    def get_data(self, variable, date=None):
        if variable != self._current_variable: # read data from disk
            with Dataset(self.path, 'r') as ds:
                slice_to_read = slice(None)
                # If it has a time dimension but no coord var we treat it as non-temporal
                if len(ds.variables[variable].shape) == 3 and not self.time_info.is_temporal:
                    slice_to_read = -1
                self._current_grid = ds.variables[variable][slice_to_read]
            self._current_variable = variable

        slice_to_return = slice(None)
        if self.time_info.is_temporal:
            if date is None:
                date = Timeline.app().current
            slice_to_return = min([i for i in enumerate(self.time_info.timestamps)],
                key=lambda d: abs(d[1] - date))[0]
        return self._current_grid[slice_to_return]

    @property
    def shape(self):
        return self.var_shape

    @property
    def resolution(self):
        return self._resolution

    def calculate_stats(self):
        with Dataset(self.path, 'r') as ds:
            desc = clover.netcdf.describe.describe(ds)
            for var in self.variables:
                v_desc = desc['variables'][var]
                self.stats[var] = VariableStats(v_desc['min'], v_desc['max'],
                    get_fill_value_for_variable(ds.variables[var]))
