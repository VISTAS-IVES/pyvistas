import numpy
import os

from vistas.core.plugins.data import ArrayDataPlugin


class TestPlugin(ArrayDataPlugin):
    id = 'test_data_plugin'
    name = 'Test Data Plugin'
    description = 'A plugin to test data plugin functionality. Loads RGB values from a text file.'
    author = 'Conservation Biology Institute'
    extensions = [('txt', 'Text File')]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.data = None

    def load_data(self):
        with open(self.path, 'r') as f:
            self.data = numpy.array([int(x.strip()) for x in f.read().split(',')])

    @property
    def data_name(self):
        return os.path.splitext(os.path.split(self.path)[-1])[0]

    @staticmethod
    def is_valid_file(path):
        return True

    def get_data(self, variable):
        return self.data
