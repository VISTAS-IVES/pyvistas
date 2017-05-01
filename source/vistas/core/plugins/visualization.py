from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.interface import Plugin


class VisualizationPlugin(Plugin):
    @property
    def can_visualize(self):
        """ Returns True if the visualization has the necessary data to be shown """

        raise NotImplemented

    @property
    def visualization_name(self):
        raise NotImplemented

    @property
    def data_roles(self):
        raise NotImplemented

    def set_data(self, data: DataPlugin, role):
        """ Set data in a specific role for the visualization """

        raise NotImplemented

    def get_data(self, role) -> DataPlugin:
        """ Get the data associated with a specific role """

        raise NotImplemented

    def set_filter(self, min_value, max_value):
        """ Set the filter min/max for the visualization """

        pass

    def clear_filter(self):
        """ Clear any filter for this visualization """

        pass

    @property
    def is_filterable(self):
        """ Can the visualization be filtered? """

        return False

    @property
    def filter_histogram(self):
        """ A histogram representing data in the visualization which can be filtered """

        return None

    @property
    def is_filtered(self):
        return False

    @property
    def filter_min(self):
        return 0

    @property
    def filter_max(self):
        return 0

    def has_legend(self):
        """ Does the visualization have a legend? """

        return False


class VisualizationPlugin2D(VisualizationPlugin):
    def visualize(self, width, height, back_thread=True):
        """ 
        Actualize the visualization. Returns the visualization if `back_thread` is False, otherwise generates an event 
        when the visualization is ready. 
        """

        NotImplemented  # Todo

    def render(self, width, height):
        """ Implemented by plugins to render the visualization """

        raise NotImplemented


class VisualizationPlugin3D(VisualizationPlugin):
    def set_scene(self, scene):
        """ Set the scene the visualization exists in. The visualization won't appear until a scene has been set. """

        raise NotImplemented

    def refresh(self):
        """ 
        Signals the visualization to refresh itself if needed. E.g., after changing the configuration or setting new 
        data. 
        """

        pass

    @property
    def scene(self):
        raise NotImplemented
