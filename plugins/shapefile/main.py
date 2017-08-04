import os
import json
import fiona
from osgeo import ogr
from pyproj import Proj

from vistas.core.gis.extent import Extent
from vistas.core.plugins.data import FeatureDataPlugin, VariableStats, TemporalInfo


class Shapefile(FeatureDataPlugin):

    id = 'shapefile'
    name = 'Shapefile Data Plugin'
    description = 'A plugin to read shapefiles (.shp)'
    author = 'Conservation Biology Institute'
    version = '1.0'
    extensions = [('shp', 'Shapefile')]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._name = None
        self.metadata = None
        self._extent = None

    def load_data(self):

        self._name = self.path.split(os.sep)[-1].split('.')[0]

        with fiona.open(self.path, 'r') as shp:
            self.metadata = shp.meta
            projection = Proj(init=self.metadata['crs']['init'])

        driver = ogr.GetDriverByName('ESRI Shapefile')
        src = driver.Open(self.path, 0)

        if src is None:
            print("OGR Failed...")
        else:
            layer = src.GetLayer()
            self._num_features = layer.GetFeatureCount()
            xmin, xmax, ymin, ymax = layer.GetExtent()
            self._extent = Extent(xmin, ymin, xmax, ymax, projection)

    @property
    def data_name(self):
        return self._name

    @staticmethod
    def is_valid_file(path):
        return True

    @property
    def extent(self):
        return self._extent

    @property
    def time_info(self):
        return TemporalInfo()  # Todo - implement ENVISION-style pattern matching for time-enabled shapefiles

    @property
    def variables(self):
        return list(self.metadata['schema']['properties'].keys())

    @property
    def has_stats(self):
        return os.path.exists(self.path.replace('.shp', '.json'))

    def calculate_stats(self):
        variables = self.variables
        if self.stats.is_stale:
            all_stats = [(var, VariableStats()) for var in self.variables]
            with fiona.open(self.path, 'r') as shp:
                for feature in shp:
                    for i, var in enumerate(variables):
                        stats = all_stats[i][1]
                        value = feature['properties'][var]

                        if isinstance(value, (int, float)):
                            if stats.max_value is None:
                                stats.max_value = stats.min_value = value
                            else:
                                if stats.max_value < value:
                                    stats.max_value = value
                                elif stats.min_value > value:
                                    stats.min_value = value

                        elif isinstance(value, str):
                            misc = stats.misc
                            if 'unique_values' not in misc:
                                misc['unique_values'] = []
                            if value not in misc['unique_values']:
                                misc['unique_values'].append(value)

            for var, stats in all_stats:
                self.stats[var] = stats
            self.save_stats()

    def get_features(self, date=None):
        with fiona.open(self.path, 'r') as shp:
            yield from shp
