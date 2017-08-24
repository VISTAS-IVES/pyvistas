from xml.etree import ElementTree

from vistas.core.color import RGBColor
from vistas.core.graphics.features import FeatureLayer
from vistas.core.graphics.tile import TileLayerRenderable
from vistas.core.legend import StretchedLegend, CategoricalLegend
from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.option import Option, OptionGroup
from vistas.core.plugins.visualization import VisualizationPlugin3D
from vistas.core.timeline import Timeline
from vistas.ui.utils import *


GREY = RGBColor(0.5, 0.5, 0.5)


class EnvisionVisualization(VisualizationPlugin3D):

    id = 'envision_tiles_viz'
    name = 'Envision'
    description = 'Terrain visualization with features'
    author = 'Conservation Biology Institute'
    version = '1.0'
    visualization_name = 'Envision'

    def __init__(self):
        super().__init__()

        self._scene = None

        # Renderable objects for this scene
        self.tile_layer = None
        self.feature_layer = None
        self.feature_data = None
        self.delta_data = None

        # Delta array access
        self.current_delta_array = None
        self.current_delta = None

        # Flags for rendering
        self.needs_mesh = False
        self.needs_color = False
        self.current_attribute = None
        self.legend = None
        self.envision_style = None

        # Options
        self._attributes = Option(self, Option.CHOICE, 'Attributes', 0)
        self._zoom = Option(self, Option.SLIDER, 'Zoom Level', 9, 5, 11, 1)
        self._transparency = Option(self, Option.SLIDER, 'Transparency', 0.75, 0.0, 1.0, 0.1)
        self._height = Option(self, Option.SLIDER, 'Height Multiplier', 1.0, 0.01, 5.0, 0.01)
        self._offset = Option(self, Option.FLOAT, 'Height Offset', 5, 0, 10)
        self._delta_toggle = Option(self, Option.CHECKBOX, 'Use Deltas', False)
        self._options = OptionGroup()
        self._options.items = [
            self._attributes, self._zoom, self._transparency, self._height, self._offset, self._delta_toggle
        ]

    @property
    def use_deltas(self):
        return self._delta_toggle.value

    def get_options(self):
        return self._options

    def update_option(self, option=None):
        if option.plugin is not self:
            return

        # Update zoom layer for map
        if option.name == self._zoom.name:
            zoom = int(self._zoom.value)
            if self.tile_layer and zoom != self.tile_layer.zoom:
                self.tile_layer.zoom = zoom

            if self.feature_layer and zoom != self.feature_layer.zoom:
                self.feature_layer.zoom = zoom
                self.feature_layer.render(self._scene)

        elif option.name == self._transparency.name:
            if self.feature_layer:
                self.feature_layer.renderable.transparency = self._transparency.value

        elif option.name == self._attributes.name:
            if self._attributes.selected != self.current_attribute:
                self.current_attribute = self._attributes.selected
                self.needs_color = True

        elif option.name == self._height.name:
            multiplier = self._height.value
            if self.tile_layer:
                self.tile_layer.height_multiplier = multiplier
            if self.feature_layer:
                self.feature_layer.renderable.height_multiplier = multiplier

        elif option.name == self._offset.name:
            offset = self._offset.value
            if self.feature_layer:
                self.feature_layer.renderable.height_offset = offset

        elif option.name == self._delta_toggle.name:
            if self.delta_data and self.delta_data.time_info.is_temporal and \
                    self.is_delta_attribute(self.current_attribute):
                self.needs_color = True

        self.refresh()

    def update_colors(self):
        # Here we determine what type and how we are going to render the viz. Then we're going to send a render request
        sample_feature = next(self.feature_data.get_features())
        props = sample_feature.get('properties')

        if self.envision_style is not None:
            value = props.get(self.envision_style[self.current_attribute].get('column'))

            if value is not None:
                self.legend = CategoricalLegend(self.envision_style[self.current_attribute].get('categories'))

                # Decide which color function to use
                if self.delta_data and self.is_delta_attribute(self.current_attribute) and self.use_deltas:
                    self.feature_layer.set_color_function(self.color_deltas)
                else:
                    self.feature_layer.set_color_function(self.color_shapes)

            else:   # Nothing to be done, color it grey
                self.legend = None
                self.feature_layer.set_color_function(None)

        else:   # Envision styling is not active
            stats = self.feature_data.variable_stats(self.current_attribute)
            value = props.get(self.current_attribute)
            self.feature_layer.set_color_function(self.color_shapes)

            if isinstance(value, (int, float)):
                min_value = stats.min_value
                max_value = stats.max_value
                min_color = RGBColor(0, 0, 1)
                max_color = RGBColor(1, 0, 0)
                self.legend = StretchedLegend(min_value, max_value, min_color, max_color)

            elif isinstance(value, str):
                categories = [(RGBColor.random(), label) for label in stats.misc['unique_values']]
                self.legend = CategoricalLegend(categories)

            else:
                self.legend = None

        if self.needs_color:
            self.feature_layer.needs_color = True
            self.feature_layer.render(self.scene)

    def is_delta_attribute(self, variable):
        return self.envision_style[variable].get('column') in self.delta_data.variables

    def timeline_changed(self):
        if self.feature_data and self.delta_data:
            self.needs_color = self.use_deltas and \
                               self.delta_data.time_info.is_temporal and \
                               self.is_delta_attribute(self.current_attribute)
        self.refresh()

    def get_legend(self, width, height):
        if self.legend is not None:
            return self.legend.render(width, height)
        else:
            return None

    def has_legend(self):
        return self.legend is not None

    @property
    def can_visualize(self):
        return self.feature_data is not None

    @property
    def data_roles(self):
        return [
            (DataPlugin.FEATURE, 'Shapefile'),
            (DataPlugin.ARRAY, 'Delta Array')
        ]

    def parse_envision_style(self):
        document = ElementTree.parse(self.feature_data.path.replace('.shp', '.xml'))
        root = document.getroot()

        # Parse the envision xml style one time into a dictionary
        data = {}
        for submenu in root:
            for field in submenu:
                field_data = dict(field.items())
                col = field_data.get('col')
                label = field_data.get('label')
                field_data = {'column': col, 'label': label}
                for piece in field:
                    if piece.tag != 'attributes':
                        continue
                    attr_data = [dict(attr.items()) for attr in piece]
                    field_data.update({'legend': attr_data})
                data[label] = field_data
        self.envision_style = data

        # Make colors by category
        empties = []
        for column in self.envision_style:
            legend = self.envision_style[column].get('legend')

            if not legend:              # If legend doesn't exist or the length is 0, discard from the style
                empties.append(column)
                continue

            categories = []
            for data in legend:
                color = RGBColor(*[int(x) / 255 for x in data.get('color')[1:-1].split(',')])
                label = data.get('label')
                categories.append((color, label))
            self.envision_style[column]['categories'] = categories

            if 'minVal' in legend[0]:
                minmax = []
                for data in legend:
                    minmax.append((float(data.get('minVal')), float(data.get('maxVal'))))
                self.envision_style[column]['minmax'] = minmax

        for column in empties:
            self.envision_style.pop(column)

        # Remove variables from style that are not in the shapefile
        variables = self.feature_data.variables
        keys = list(self.envision_style.keys())
        for key in keys:
            column = self.envision_style[key].get('column')
            if column not in variables:
                self.envision_style.pop(key)

    def set_data(self, data: DataPlugin, role):
        if role == 0:
            self.feature_data = data
            self.needs_mesh = True
            self.needs_color = True

            if self.feature_data is not None:
                try:
                    self.parse_envision_style()
                    self._attributes.labels = list(self.envision_style.keys())
                    self.current_attribute = self._attributes.labels[0]

                except (ElementTree.ParseError, ValueError, FileNotFoundError):
                    post_message("XML parsing failed, defaulting to feature schema.", 1)

                    # Use shapefile colors instead
                    self.envision_style = None
                    self._attributes.labels = self.feature_data.variables
                    self.current_attribute = self._attributes.labels[0]
            else:
                self._attributes.labels = []
                self.current_attribute = None
                self.envision_style = None

        elif role == 1:
            if not isinstance(data, VisualizationPlugin3D.by_name('envision_delta_reader')):
                raise ValueError("Delta Array role must use the Envision Delta Array Data Plugin.")
            self.delta_data = data

    def get_data(self, role):
        if role == 0:
            return self.feature_data
        elif role == 1:
            return self.delta_data
        return None

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
        if self.needs_mesh:
            self.create_terrain_mesh()
            self.needs_mesh = False
        if self.needs_color:
            self.update_colors()
            self.needs_color = False
        post_redisplay()

    def create_terrain_mesh(self):
        if self.feature_data is not None:
            zoom = int(self._zoom.value)
            self.tile_layer = TileLayerRenderable(self.feature_data.extent, zoom=zoom)
            self.scene.add_object(self.tile_layer)
            self.feature_layer = FeatureLayer(self.feature_data, zoom=zoom)
            self.feature_layer.set_color_function(self.color_shapes)
        else:
            self.scene.remove_all_objects()
            self.tile_layer = None
            self.feature_layer = None

    def color_shapes(self, feature):
        """
        Color features based either on Envision XML style or on a generic color scheme derived from the feature schema.
        """

        if self.current_attribute is None or self.legend is None:
            return GREY

        if self.envision_style is not None:
            envision_attribute = self.envision_style[self.current_attribute]
            shp_attribute = envision_attribute.get('column')
            legend = envision_attribute.get('legend')
            value = feature.get('properties').get(shp_attribute)
            minmax = envision_attribute.get('minmax', None)
            string_value = ''

            if minmax is not None:
                for i, pair in enumerate(minmax):
                    if pair[0] <= value <= pair[1]:
                        string_value = legend[i].get('label')
                        break
            else:
                for entry in legend:
                    try:
                        val = float(entry.get('value'))
                    except ValueError:
                        continue
                    if val == value:
                        string_value = entry.get('label')
                        break

            color = self.legend.get_color(string_value)
            if color is None:
                color = GREY
            return color

        # Fallback to coloring based on shapefile schema
        else:
            value = feature.get('properties').get(self.current_attribute)
            return self.legend.get_color(value)

    def color_deltas(self, feature):
        """
        Color features based on presence in the Envision Delta Array. Features absent from delta array are colored grey.
        """

        if self.legend is None:
            return GREY

        envision_attribute = self.envision_style[self.current_attribute]
        shp_attribute = envision_attribute.get('column')
        legend = envision_attribute.get('legend')
        value = feature.get('properties').get(shp_attribute)
        idu = int(feature.get('id'))
        minmax = envision_attribute.get('minmax', None)
        string_value = ''

        if self.current_delta_array is None:
            delta_array_generator = self.delta_data.get_data(shp_attribute, Timeline.app().current)
            if delta_array_generator is not None:
                self.current_delta_array = delta_array_generator
                self.current_delta = next(self.current_delta_array)
            else:
                self.feature_layer.set_color_function(self.color_shapes)
                post_message("Could not retrieve deltas, defaulting to base value.", 1)
                return self.color_shapes(feature)

        try:
            if self.current_delta.idu == idu:
                value += self.current_delta.new_value
                self.current_delta = next(self.current_delta_array)
            else:
                if self.current_delta.idu < idu:
                    while self.current_delta.idu <= idu:
                        self.current_delta = next(self.current_delta_array)

                return GREY

        # Handle if we reached the end of the delta array
        except StopIteration:
            self.current_delta_array = None
            return GREY

        if minmax is not None:
            for i, pair in enumerate(minmax):
                if pair[0] <= value <= pair[1]:
                    string_value = legend[i].get('label')
                    break

        color = self.legend.get_color(string_value)
        if color is None:
            color = GREY

        return color
