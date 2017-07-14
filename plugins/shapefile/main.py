import os
import fiona
from pyproj import Proj

from vistas.core.timeline import Timeline
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
        self._stats = None

    def load_data(self):

        self._name = self.path.split(os.sep)[-1].split('.')[0]

        with fiona.open(self.path, 'r') as shp:
            self.metadata = shp.meta
            projection = Proj(init=self.metadata['crs']['init'])

            # Determine extent
            def explode(coords):
                """ Borrowed from sgilles - https://gis.stackexchange.com/questions/90553/fiona-get-each-feature-extent-bounds
                Explode a GeoJSON geometry's coordinates object and yield coordinate tuples.
                As long as the input is conforming, the type of the geometry doesn't matter."""
                for e in coords:
                    if isinstance(e, (float, int)):
                        yield coords
                        break
                    else:
                        for inner_coords in explode(e):
                            yield inner_coords

            def bbox(feature):
                x, y = zip(*list(explode(feature['geometry']['coordinates'])))
                return min(x), min(y), max(x), max(y)

            xmin, ymin, xmax, ymax = [None] * 4

            for f in shp:
                if xmin is None:
                    xmin, ymin, xmax, ymax = bbox(f)
                else:
                    _xmin, _ymin, _xmax, _ymax = bbox(f)
                    xmin, ymin, xmax, ymax = \
                        min([xmin, _xmin]), min([ymin, _ymin]), max([xmax, _xmax]), max([ymax, _ymax])

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

    def variable_stats(self, variable):
        for stats in self._stats:
            if stats[0] == variable:
                return stats[1]
        return None

    @property
    def variables(self):
        return list(self.metadata['schema']['properties'].keys())

    def calculate_stats(self):

        variables = self.variables
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

                        misc['unique_values'].append(value)

        self._stats = all_stats

    def get_features(self, date=None):
        with fiona.open(self.path, 'r') as shp:
                features = [f for f in shp]
        return features
