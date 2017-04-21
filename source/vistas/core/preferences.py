import json
import os

import wx


class Preferences:
    _app_preferences = None

    @classmethod
    def app(cls):
        """ Application preferences """

        if cls._app_preferences is None:
            cls._app_preferences = Preferences(
                os.path.join(wx.StandardPaths.Get().UserConfigDir, 'VISTAS', 'preferences.json')
            )

        return cls._app_preferences

    def __init__(self, path):
        self.path = path
        self.preferences = {}

        self.load()

    def load(self):
        self.preferences = {}

        if os.path.exists(self.path):
            with open(self.path) as f:
                self.preferences = json.load(f)

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(f)

    def __getitem__(self, key):
        return self.preferences[key]

    def __setitem__(self, key, value):
        if key in self.preferences and self.preferences[key] == value:
            return

        self.preferences[key] = value
        self.save()

    def get(self, key):
        return self.preferences.get(key)
