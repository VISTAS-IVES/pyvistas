import json
import os

import wx

from vistas.core.utils import get_platform, get_config_dir


class Preferences:
    """ Application preferences cache. """

    _app_preferences = None

    @classmethod
    def app(cls):
        """ Application preferences """

        if cls._app_preferences is None:
            path = os.path.join(get_config_dir(), 'preferences.json')
            dir = os.path.dirname(path)
            if not os.path.exists(dir):
                os.makedirs(os.path.dirname(path))

            cls._app_preferences = Preferences(path)

        return cls._app_preferences

    def __init__(self, path):
        self.path = path
        self.preferences = {}

        self.load()

    def load(self):
        self.preferences = {}

        if os.path.exists(self.path):
            with open(self.path, 'r') as f:
                self.preferences = json.load(f)

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.preferences, f)

    def __getitem__(self, key):
        return self.preferences[key]

    def __setitem__(self, key, value):
        if key in self.preferences and self.preferences[key] == value:
            return

        self.preferences[key] = value
        self.save()

    def get(self, key, default=None):
        return self.preferences.get(key, default)
