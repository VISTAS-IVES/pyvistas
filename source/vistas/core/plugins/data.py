from vistas.core.plugins.interface import Plugin


class VariableStats:
    """ Variable statistics interface """

    def __init__(self, min_value=None, max_value=None, nodata_value=None, misc={}):
        self.min_value = min_value
        self.max_value = max_value
        self.nodata_value = nodata_value
        self.misc = misc

    @property
    def to_dict(self):
        inputs = {'min_value': self.min_value, 'max_value': self.max_value, 'nodata_value': self.nodata_value}
        return {**inputs, **self.misc}

    @classmethod
    def from_dict(cls, d):
        min_value = d.pop('min_value')
        max_value = d.pop('max_value')
        nodata_value = d.pop('nodata_value')
        return cls(min_value, max_value, nodata_value, d)


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

    def set_path(self, path):
        """ Set the path to the data """

        self.path = path
        self.load_data()

    def load_data(self):
        """ Hook implemented by subclasses to load data after a call to `set_path()` """

        pass

    @property
    def data_name(self):
        raise NotImplemented

    @property
    def size(self):
        """ Get the size of the data on disk """

        raise NotImplemented  # Todo

    @property
    def extent(self):
        """ Returns an extent (bounding box) object for the data, if applicable """

        return None

    @property
    def time_info(self) -> TemporalInfo or None:
        """ Get time info for the data, if applicable """

        return None

    def variable_stats(self, variable) -> VariableStats or None:
        """ Get the statistics calculated for the variable, if applicable """

        return None

    @property
    def variables(self):
        """ Returns a list of variables for the data """

        raise NotImplemented

    @staticmethod
    def is_valid_file(path):
        return False

    def calculate_stats(self):
        """ Perform statistics for the data. """

        pass


class ArrayDataPlugin(DataPlugin):
    """ Base class for 1-dimensional array data """

    data_type = DataPlugin.ARRAY

    def get_data(self, variable):
        """Returns a numpy array """


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

    def get_data(self, variable, date=None):
        """ Returns a numpy array for the data at the given time """

        raise NotImplemented


class FeatureDataPlugin(DataPlugin):
    """ Base class for feature data (e.g., shapefile) """

    data_type = DataPlugin.FEATURE

    def get_features(self, date=None):
        """ Returns an array of shapely features for the given time """

        raise NotImplemented
