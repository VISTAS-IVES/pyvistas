import os

import wx
from PIL import Image

from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.interface import Plugin
from vistas.core.threading import Thread
from vistas.ui.utils import get_main_window

RenderEvent, EVT_VISUALIZATION_RENDERED = wx.lib.newevent.NewEvent()
VisualizationUpdateEvent, EVT_VISUALIZATION_UPDATED = wx.lib.newevent.NewEvent()


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

    def role_supports_multiple_inputs(self, role):
        """ Returns whether the role can have multiple sub-roles """
        return False

    def role_supports_variable_inputs(self, role):
        """ Returns whether the role can have a variadic number of sub-roles """
        return False

    def role_size(self, role):
        """ Get the number of inputs for a specific role """
        return 1

    def set_data(self, data: DataPlugin, role):
        """ Set data in a specific role for the visualization """

        raise NotImplemented

    def get_data(self, role) -> DataPlugin:
        """ Get the data associated with a specific role """

        raise NotImplemented

    def get_multiple_data(self, role) -> [DataPlugin]:
        """ Get a list of data plugins associated with a specific role """
        return []

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

    def get_legend(self, width, height):
        """ A color legend for the visualization """

        return None


class VisualizationPlugin2D(VisualizationPlugin):
    class RenderThread(Thread):
        def __init__(self, plugin, width, height, handler=None):
            super().__init__()

            self.plugin = plugin
            self.width = width
            self.height = height
            self.handler = handler

        def run(self):
            event = RenderEvent(image=self.plugin.render(self.width, self.height))
            handler = self.handler if self.handler is not None else get_main_window()

            wx.PostEvent(handler, event)

    def visualize(self, width, height, back_thread=True, handler=None):
        """
        Actualize the visualization. Returns the visualization if `back_thread` is False, otherwise generates an event
        when the visualization is ready.
        """

        if not back_thread:
            return self.render(width, height)

        self.RenderThread(self, width, height, handler).start()

    def render(self, width, height) -> Image:
        """ Implemented by plugins to render the visualization """

        raise NotImplemented


class VisualizationPlugin3D(VisualizationPlugin):
    @property
    def scene(self):
        raise NotImplemented

    @scene.setter
    def scene(self, scene):
        """ Set the scene the visualization exists in. The visualization won't appear until a scene has been set. """

        raise NotImplemented

    def get_shader_path(self, name):
        """ Returns an absolute path to a plugin shader by file name """

        return os.path.join(self.plugin_dir, 'shaders', name)

    def refresh(self):
        """
        Signals the visualization to refresh itself if needed. E.g., after changing the configuration or setting new
        data.
        """

        pass

    @property
    def scene(self):
        raise NotImplemented
