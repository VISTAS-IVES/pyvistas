import copy
import math
from itertools import product

from mercantile import tiles
from pyproj import Proj, transform


class Extent:
    """
    Encapsulates geographic bounding box related logic with associated projection information (must be a pyproj
    projection object).
    """

    def __init__(self, xmin, ymin, xmax, ymax, projection=None):

        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        self.projection = None

        if projection:
            assert isinstance(projection, Proj)
            self.projection = projection

    @property
    def width(self):
        return abs(self.xmax - self.xmin)

    @property
    def height(self):
        return abs(self.ymax - self.ymin)

    def __unicode__(self):
        return str(self.as_list())

    def __repr__(self):
        return str(self.as_list())

    @classmethod
    def from_affine(cls, affine, width, height, projection=None):
        """
        Return new BBox object based on an Affine object
        """
        return cls(
            (affine.c, affine.f + affine.e * height, affine.c + affine.a * width, affine.f),
            projection=projection
        )

    def clone(self):
        return copy.copy(self)

    def as_list(self):
        return [getattr(self, key) for key in ("xmin", "ymin", "xmax", "ymax")]

    def as_dict(self):
        info = {key: getattr(self, key) for key in ("xmin", "ymin", "xmax", "ymax")}
        if self.projection:
            info['proj4'] = self.projection.srs
        return info

    def is_geographic(self):
        return self.projection.is_latlong()

    def tiles(self, zoom):
        return list(tiles(*self.project(Proj(init='EPSG:4326')).as_list(), [zoom]))

    def project(self, target_projection, edge_points=9):
        """
        target_projection must be a pyproj projection.
        Densifies the edges with edge_points points between corners, and projects all of them.
        Returns the outer bounds of the projected coords.
        Note: beware projection issues when going to projections that don't fully encapsulate the world domain
        (e.g., Web Mercator has singularities above and below latitudes of ~ 85).
        """

        assert self.projection and isinstance(target_projection, Proj)

        if target_projection.srs == self.projection.srs:
            return self.clone()

        if edge_points < 2:
            # use corners only
            x_values, y_values = transform(self.projection, target_projection, [self.xmin, self.xmax], [self.ymin, self.ymax])
            return Extent(*(x_values[0], y_values[0], x_values[1], y_values[1]), projection=target_projection)

        samples = range(0, edge_points)
        xstep = float(self.xmax - self.xmin) / (edge_points - 1)
        ystep = float(self.ymax - self.ymin) / (edge_points - 1)
        x_values = []
        y_values = []
        for i, j in product(samples, samples):
            x_values.append(self.xmin + xstep * i)
            y_values.append(self.ymin + ystep * j)

        x_values, y_values = transform(self.projection, target_projection, x_values, y_values)
        return Extent(min(x_values), min(y_values), max(x_values), max(y_values), target_projection)

    def get_local_albers_projection(self):
        """
        Project bbox to geographic coordinates, create a custom Albers projection centered over the bbox that minimizes
        area distortions.  Uses 1/6 inset from ymin and ymax to define latitude bounds, and centerline between xmin and xmax
        to define central meridian.
        Coordinates must be within the world domain.
        """

        inset_factor = 1.0 / 6.0
        geo_bbox = self.project(Proj(init="EPSG:4326"))
        # Make sure we are within world domain
        assert geo_bbox.xmin >= -180 and geo_bbox.xmax <= 180 and geo_bbox.ymin >= -90 and geo_bbox.ymax <= 90
        inset = math.fabs((geo_bbox.ymax - geo_bbox.ymin) * inset_factor)
        return Proj(proj='aea', lat_1=geo_bbox.ymin + inset, lat_2=geo_bbox.ymax - inset, lat_0=0,
                    lon_0=((geo_bbox.xmax - geo_bbox.xmin) / 2.0) + geo_bbox.xmin,
                    x_0=0, y_0=0, ellps='WGS84', datum='WGS84', units='m', no_defs=True)


def union_bbox(bboxes):
    """
    Return the extent that includes all bounding boxes. Resulting extent projection will use first bounding box
    projection in list.
    """

    bboxes = [x for x in bboxes if x is not None]
    if not bboxes:
        return None

    x_set = {b.xmin for b in bboxes} | {b.xmax for b in bboxes}
    y_set = {b.ymin for b in bboxes} | {b.ymax for b in bboxes}

    return Extent(*(min(x_set), min(y_set), max(x_set), max(y_set)), projection=bboxes[0].projection)
