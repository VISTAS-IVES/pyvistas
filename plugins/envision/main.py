from vistas.core.color import RGBColor
from vistas.core.graphics.features import FeatureCollection
from vistas.core.graphics.tile import TileLayerRenderable
from vistas.core.legend import StretchedLegend, CategoricalLegend
from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.option import Option, OptionGroup
from vistas.core.plugins.visualization import VisualizationPlugin3D
from vistas.ui.utils import *


class EnvisionVisualization(VisualizationPlugin3D):

    id = 'envision_tiles_viz'
    name = 'Envision'
    description = 'Terrain visualization with tiles'
    author = 'Conservation Biology Institute'
    version = '1.0'
    visualization_name = 'Envision (Tiles)'

    def __init__(self):
        super().__init__()

        # This plugin's scene
        self._scene = None

        # Renderable objects for this scene
        self.tile_layer = None
        self.feature_collection = None
        self.data = None

        # Flags for rendering
        self._needs_mesh = False

        # Options
        self._zoom = Option(self, Option.SLIDER, 'Zoom Level', 9, 5, 11, 1)
        self._transparency = Option(self, Option.SLIDER, 'Transparency', 0.75, 0.0, 1.0, 0.1)
        self._attributes = Option(self, Option.CHOICE, 'Attributes', 0)
        self._options = OptionGroup()
        self._options.items = [self._zoom, self._transparency, self._attributes]

        # Coloring
        self.current_attribute = None
        self.legend = None

    def get_options(self):
        return self._options

    def update_option(self, option=None):
        if option.plugin is not self:
            return

        # Update zoom layer for map
        if option.name == self._zoom.name:
            zoom = int(self._zoom.value)

            if self.tile_layer is not None:
                if zoom != self.tile_layer.zoom:
                    self.tile_layer.zoom = zoom
                    self.tile_layer.render(self._scene)

            if self.feature_collection is not None:
                if zoom != self.feature_collection.zoom:
                    self.feature_collection.zoom = zoom
                    self.feature_collection.render(self._scene)

        elif option.name == self._transparency.name:
            if self.feature_collection is not None:
                self.feature_collection.renderable.set_transparency(self._transparency.value)

        elif option.name == self._attributes.name:
            if self._attributes.selected != self.current_attribute:
                self.current_attribute = self._attributes.selected
                self.update_colors()

        self.refresh()

    def update_colors(self):

        # Here we determine what type and how we are going to render the viz. Then we're going to send a render request
        stats = self.data.variable_stats(self.current_attribute)
        sample_feature = next(self.data.get_features())

        props = sample_feature.get('properties')
        value = props.get(self.current_attribute)

        # Todo - get color labels from Envision XML

        if isinstance(value, (int, float)):
            min_value = stats.min_value
            max_value = stats.max_value
            min_color = RGBColor(0, 0, 1)
            max_color = RGBColor(1, 0, 0)
            self.legend = StretchedLegend(min_value, max_value, min_color, max_color)

        elif isinstance(value, str):
            categories = [(RGBColor.random(), label) for label in stats.misc['unique_values']]
            self.legend = CategoricalLegend(categories)

        else:                   # Nothing to be done, color it grey
            self.legend = None

        self.feature_collection.needs_color = True
        self.feature_collection.render(self._scene)

    def get_legend(self, width, height):
        if self.legend is not None:
            return self.legend.render(width, height)
        else:
            return None

    @property
    def can_visualize(self):
        return self.data is not None

    @property
    def data_roles(self):
        return [
            (DataPlugin.FEATURE, 'Shapefile')
        ]

    def set_data(self, data: DataPlugin, role):
        self.data = data
        self._needs_mesh = True

        if self.data is not None:
            self._attributes.labels = list(self.data.variables)
            self.current_attribute = self._attributes.labels[0]
        else:
            self._attributes.labels = []
            self.current_attribute = None

    def get_data(self, role):
        return self.data

    @property
    def scene(self):
        return self._scene

    @scene.setter
    def scene(self, scene):
        if self._scene is not None:
            if self.tile_layer:
                self._scene.remove_object(self.tile_layer)

        self._scene = scene

        if self.tile_layer and self._scene is not None:
            self._scene.add_object(self.tile_layer)

    def refresh(self):
        if self._needs_mesh:
            self._create_terrain_mesh()
            self._needs_mesh = False
        post_redisplay()

    def _create_terrain_mesh(self):
        if self.data is not None:
            zoom = int(self._zoom.value)
            self.tile_layer = TileLayerRenderable(self.data.extent, zoom=zoom)
            self.scene.add_object(self.tile_layer)
            self.feature_collection = FeatureCollection(self.data, self.tile_layer.cellsize, zoom=zoom)

            # Register the color function. This operates on each feature in the collection, and determines how we
            # we want to color the feature
            self.feature_collection.set_color_function(self.color_feature)
            self.feature_collection.render(self.scene)
        else:
            self.scene.remove_all_objects()
            self.tile_layer = None
            self.feature_collection = None

    def color_feature(self, feature):
        if self.current_attribute is None or self.legend is None:
            return RGBColor(0.5, 0.5, 0.5)

        else:
            value = feature.get('properties').get(self.current_attribute)
            return self.legend.get_color(value)
