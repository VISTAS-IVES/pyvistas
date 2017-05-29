import os
import fiona

from vistas.core.timeline import Timeline
from vistas.core.gis.extent import Extent
from vistas.core.plugins.data import FeatureDataPlugin


class Shapefile(FeatureDataPlugin):

    id = 'shapefile'
    name = 'Shapefile Data Plugin'
    description = 'A plugin to read shapefiles (.shp)'
    author = 'Conservation Biology Institute'
    extensions = [('shp', 'Shapefile'), ('json', 'GeoJSON')]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._name = None
        self.metadata = None
        self.features = None

    def load_data(self):

        self._name = self.path.split(os.sep)[-1].split('.')[0]

        with fiona.open(self.path, 'r') as shp:
            self.metadata = shp.meta
            self.features = [f for f in shp]

        print(self.features)
        print(self.metadata)

    @property
    def data_name(self):
        return self._name

    @staticmethod
    def is_valid_file(path):
        return True

    @property
    def extent(self):

        return None  # Todo - construct extent from self.metadata

    @property
    def time_info(self):

        return None  # Todo - implement ENVISION-style pattern matching for regex

    def variable_stats(self, variable):

        return None  # Todo - implement stats for each feature that we get

    @property
    def variables(self):

        raise NotImplemented    # Todo - get a list of variable names from the features

    def calculate_stats(self):

        pass  # Todo - calculate stats

    def get_features(self, date=None):

        raise NotImplemented    # Todo - construct shapely feature set
