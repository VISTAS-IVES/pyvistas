import os
import fiona
from pyproj import Proj
from shapely.geometry import Point, Polygon

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
        self._extent = None

    def load_data(self):

        self._name = self.path.split(os.sep)[-1].split('.')[0]

        with fiona.open(self.path, 'r') as shp:
            self.metadata = shp.meta
            features = [f for f in shp]

        def explode(coords):
            """ Borrowed from sgilles - https://gis.stackexchange.com/questions/90553/fiona-get-each-feature-extent-bounds
            Explode a GeoJSON geometry's coordinates object and yield coordinate tuples.
            As long as the input is conforming, the type of the geometry doesn't matter."""
            for e in coords:
                if isinstance(e, (float, int)):
                    yield coords
                    break
                else:
                    for f in explode(e):
                        yield f

        def bbox(feature):
            x, y = zip(*list(explode(feature['geometry']['coordinates'])))
            return min(x), min(y), max(x), max(y)

        projection = Proj(init=self.metadata['crs']['init'])

        self.features = []
        xmin, ymin, xmax, ymax = [None] * 4

        for f in features:
            if xmin is None:
                xmin, ymin, xmax, ymax = bbox(f)
            else:
                _xmin, _ymin, _xmax, _ymax = bbox(f)
                xmin, ymin, xmax, ymax = min([xmin, _xmin]), min([ymin, _ymin]), max([xmax, _xmax]), max([ymax, _ymax])

            # Convert feature geometry into shapely objects
            geometry_type = f['geometry']['type']

            if geometry_type == 'Polygon':
                try:
                    self.features.append(Polygon(f['geometry']['coordinates']))
                except:
                    try:
                        self.features.append(Polygon(f['geometry']['coordinates'][0]))
                    except:
                        raise TypeError("Cannot import geometry, shapefile is malformed...")

            elif geometry_type == 'Point':
                pass    # Todo - implement support for points

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

        return None  # Todo - implement ENVISION-style pattern matching for regex

    def variable_stats(self, variable):

        return None  # Todo - implement stats for each feature that we get

    @property
    def variables(self):
        return list(self.metadata['schema']['properties'].keys())

    def calculate_stats(self):

        pass  # Todo - calculate stats?

    def get_features(self, date=None):
        return self.features
