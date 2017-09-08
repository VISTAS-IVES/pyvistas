import os
from typing import Optional

from vistas.core.stats import PluginStats, VariableStats
from vistas.core.gis.extent import Extent
from vistas.core.plugins.interface import Plugin


class TemporalInfo:
    """ Temporal info for data plugins """

    def __init__(self):
        self.timestamps = []

    @property
    def is_temporal(self):
        return len(self.timestamps) > 0


class DataPlugin(Plugin):
    ARRAY = 'array'
    RASTER = 'raster'
    FEATURE = 'feature'

    extensions = []  # A list of extensions this plugin can load
    data_type = None

    def __init__(self):
        self.path = None
        self.stats = None

    def set_path(self, path):
        """ Set the path to the data """

        self.path = path
        self.load_data()
        self.load_stats()

    def load_data(self):
        """ Hook implemented by subclasses to load data after a call to `set_path()` """

        pass

    @property
    def data_name(self):
        raise NotImplemented

    @property
    def size(self):
        """ Get the size of the data on disk """

        raise NotImplemented

    @property
    def extent(self) -> Optional[Extent]:
        """ Returns an extent (bounding box) object for the data, if applicable """

        return None

    @property
    def time_info(self) -> Optional[TemporalInfo]:
        """ Get time info for the data, if applicable """

        return None

    def variable_stats(self, variable) -> Optional[VariableStats]:
        """
        Get the statistics calculated for the variable, if applicable. Plugins determine whether statistics are
        calculated for a given variable.
        """

        return self.stats[variable]

    @property
    def variables(self):
        """ Returns a list of variables for the data """

        raise NotImplemented

    @staticmethod
    def is_valid_file(path):
        return False

    @property
    def stats_path(self):
        extension = self.path.split(os.sep)[-1].split('.')[-1]
        stats_path = self.path.replace('.{}'.format(extension), '.json')
        return stats_path

    def load_stats(self):
        """ Load pre-calculated statistics for a plugin. """

        if os.path.exists(self.stats_path):
            self.stats = PluginStats.load(self.stats_path, self.path, self.variables)
        else:
            self.stats = PluginStats()

    def save_stats(self):
        """
        Save pre-calculated statistics for a plugin. Overwrites cache if one exists. Plugin authors can choose not to
        use this function if statistics need to be calculated on each load.
        """

        if os.path.exists(self.stats_path):
            os.remove(self.stats_path)
        self.stats.save(self.stats_path, self.path)

    def calculate_stats(self):
        """ Perform statistics for the data. """

        pass


class ArrayDataPlugin(DataPlugin):
    """ Base class for 1-dimensional array data """

    data_type = DataPlugin.ARRAY

    def get_data(self, variable, date=None):
        """ Returns a numpy array """


class RasterDataPlugin(DataPlugin):
    """ Base class for n-dimensional raster data """

    data_type = DataPlugin.RASTER

    @property
    def shape(self):
        """ Returns the grid shape """

        raise NotImplemented

    @property
    def resolution(self):
        """ Returns the grid resolution """

        raise NotImplemented

    @property
    def affine(self):
        """ Returns the Affine transformation of the grid """

        raise NotImplemented

    def get_data(self, variable, date=None):
        """ Returns a numpy array for the data at the given time """

        raise NotImplemented


class FeatureDataPlugin(DataPlugin):
    """ Base class for feature data (e.g., shapefile) """

    data_type = DataPlugin.FEATURE

    def get_num_features(self):
        """ Returns the number of features in a feature collection. """

        raise NotImplemented

    def get_features(self, date=None):
        """ Returns an array of shapely features for the given time """

        raise NotImplemented
