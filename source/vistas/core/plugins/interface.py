import os

import inspect


class PluginBase(type):
    """ Plugin metaclass, used to register plugin classes by unique id """

    _plugins_by_name = {}

    def __new__(mcs, name, bases, attrs):
        new_class = super(PluginBase, mcs).__new__(mcs, name, bases, attrs)

        plugin_id = getattr(new_class, 'id', None)

        if plugin_id is not None:
            if plugin_id in mcs._plugins_by_name:
                raise ValueError('Two plugins exist with the id {}'.format(name))

            mcs._plugins_by_name[new_class.id] = new_class

        setattr(new_class, '_tasks_by_name', mcs._plugins_by_name)

        return new_class


class Plugin(metaclass=PluginBase):
    """ Plugin base class, extended to provide data- and viz-specific plugin classes """

    id = None
    name = None
    description = None
    author = None

    @classmethod
    def by_name(cls, name):
        return cls._plugins_by_name.get(name)

    @property
    def plugin_dir(self):
        return os.path.dirname(inspect.getfile(self.__class__))

    def get_options(self):
        return None
