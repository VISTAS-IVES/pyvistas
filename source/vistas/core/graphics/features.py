"""
FeatureCollectionRenderable - renders out features based on their shape type.

Features will be rendered out according to a
"""

import mercantile
import numpy
from OpenGL.GL import *
from pyproj import Proj, transform
from pyrr import Vector3, Matrix44
from pyrr.vector3 import generate_vertex_normals
import shapely.geometry as geometry

from vistas.core.gis.elevation import ElevationService
from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.mesh import Mesh
from vistas.core.graphics.renderable import Renderable
from vistas.core.graphics.shader import ShaderProgram
from vistas.core.paths import get_resources_directory
from vistas.core.task import Task
from vistas.core.threading import Thread
from vistas.ui.utils import post_redisplay


class FeatureMesh(Mesh):
    pass


class FeatureRenderable(Renderable):
    pass


class FeatureCollectionRenderable:
    def __init__(self, features, extent):
        self.features = [f['geometry'] for f in features]
        self.extent = extent

    @property
    def mercator_coords(self):
        mercator = self.extent.project(Proj(init='EPSG:3857')).projection
        for shp in self.features:
            shape = geometry.shape(shp)
            coords = shape.exterior.coords
            projected_coords = []
            for x1, y1 in coords:
                projected_coords.append(transform(self.extent.projection, mercator, x1, y1))
            yield projected_coords
