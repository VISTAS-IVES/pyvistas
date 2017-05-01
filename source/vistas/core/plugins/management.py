import os
from importlib.util import spec_from_file_location, module_from_spec

from vistas.core.plugins.data import DataPlugin, ArrayDataPlugin, RasterDataPlugin, FeatureDataPlugin
from vistas.core.plugins.interface import PluginBase
from vistas.core.plugins.visualization import VisualizationPlugin, VisualizationPlugin3D, VisualizationPlugin2D


def load_plugins(path):
    """ Load plugins from a directory """

    for directory in (x for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))):
        module_path = os.path.join(path, directory, 'main.py')

        if os.path.exists(module_path):
            spec = spec_from_file_location('plugin', module_path)
            mod = module_from_spec(spec)
            spec.loader.exec_module(mod)  # Plugins are registered when class definitions are executed


def get_plugins_of_type(cls):
    """ Returns all plugins of a given class """

    return [x for x in get_plugins() if isinstance(x, cls)]


def get_plugins():
    """ A list of all loaded plugins """

    return PluginBase._plugins_by_name.values()


def get_visualization_plugins():
    """ A list of all visualization plugins """

    return get_plugins_of_type(VisualizationPlugin)


def get_3d_visualization_plugins():
    """ A list of all 3D visualization plugins """

    return get_plugins_of_type(VisualizationPlugin3D)


def get_2d_visualization_plugins():
    """ A list of all 2D visualization plugins """

    return get_plugins_of_type(VisualizationPlugin2D)


def get_data_plugins():
    """ A list of all data plugins """

    return get_plugins_of_type(DataPlugin)


def get_array_data_plugins():
    """ A list of all array data plugins """

    return get_plugins_of_type(ArrayDataPlugin)


def get_raster_data_plugins():
    """ A list of all raster data plugins """

    return get_plugins_of_type(RasterDataPlugin)


def get_feature_data_plugins():
    """ A list of all feature data plugins """
    return get_plugins_of_type(FeatureDataPlugin)
