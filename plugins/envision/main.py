from vistas.core.plugins.visualization import VisualizationPlugin3D
from vistas.core.plugins.option import OptionGroup, Option
from vistas.core.legend import Legend


class EnvisionVisualizationPlugin(VisualizationPlugin3D):

    id = 'envision_viz'
    name = 'Envision Visualization'
    description = 'Displays Envision-processed shapefiles and delta arrays in 3D.'
    author = 'Conservation Biology Institute'

    def __init__(self):
        super().__init__()

        self.shape_data = None
        self.delta_data = None
        self.point_data = None

        self.current_attribute = None

        self.needs_terrain = False
        self.needs_color = False
        self.needs_points = False

        self.mesh_renderable = None
        self.points_renderabe = None

        self.options = OptionGroup()
        self.height_multiplier = Option(self, 'slider', 'Height Multiplier', 1.0, 0, 2, 0.01)
        self.light_x = Option(self, 'slider', 'Light X', 0.0, -100.0, 100.0, 1)
        self.light_y = Option(self, 'slider', 'Light Y', 100.0, -300.0, 300.0, 1)
        self.light_z = Option(self, 'slider', 'Light Z', 200.0, 0.0, 10000.0, 1)
        self.blend = Option(self, 'slider', 'Blend between terrain color and data', 1.0, 0.0, 1.0, 0.01)
        self.show_deltas = Option(self, 'checkbox', 'Show Deltas (if available)', False)
        self.show_points = Option(self, 'checkbox', 'Show Points (if available)', False)
        self._scene = None

        self.options.items = [
            self.height_multiplier, self.light_x, self.light_y, self.light_z, self.blend, self.show_deltas, self.show_points
        ]

    @property
    def scene(self):
        return self._scene

    @scene.setter
    def scene(self, scene):
        pass

    def update_option(self, option=None):
        pass

    def timeline_changed(self):
        pass

    def is_delta_attribute(self):
        pass

    def get_options(self):
        return self.options

    @property
    def data_roles(self):
        return None

    def get_data(self, role):
        return None

    def get_legend(self, width, height):
        return None

    def refresh(self):
        pass

    @property
    def geocoder_info(self):
        return None

    def create_mesh(self):
        pass

    def update_color(self):
        pass

    def update_points(self):
        pass












