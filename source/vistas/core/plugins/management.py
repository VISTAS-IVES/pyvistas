import os
from importlib.util import spec_from_file_location, module_from_spec

from vistas.core.plugins.data import DataPlugin, ArrayDataPlugin, RasterDataPlugin, FeatureDataPlugin
from vistas.core.plugins.interface import PluginBase


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

    return [x for x in plugins if isinstance(x, cls)]


@property
def plugins():
    """ A list of all loaded plugins """

    return PluginBase._plugins_by_name.values()


@property
def data_plugins():
    """ A list of all data plugins """

    return get_plugins_of_type(DataPlugin)


@property
def array_data_plugins():
    """ A list of all array data plugins """

    return get_plugins_of_type(ArrayDataPlugin)


@property
def raster_data_plugins():
    """ A list of all raster data plugins """

    return get_plugins_of_type(RasterDataPlugin)


@property
def feature_data_plugins():
    """ A list of all feature data plugins """
    return get_plugins_of_type(FeatureDataPlugin)
