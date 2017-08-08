import json
import os
import datetime


DEFAULT_CACHE_EXPIRATION = 86400  # 1 day in seconds


class VariableStats:
    """ Variable statistics interface """

    def __init__(self, min_value=None, max_value=None, nodata_value=None, misc=None):
        self.min_value = min_value
        self.max_value = max_value
        self.nodata_value = nodata_value
        self.misc = misc if misc is not None else dict()

    @property
    def to_dict(self):
        inputs = {'min_value': self.min_value, 'max_value': self.max_value, 'nodata_value': self.nodata_value}
        return {**inputs, **self.misc}

    @classmethod
    def from_dict(cls, d):
        min_value = d.pop('min_value')
        max_value = d.pop('max_value')
        nodata_value = d.pop('nodata_value')
        return cls(min_value, max_value, nodata_value, d)


class PluginStats:
    """ Plugin statistics interface. Container for a plugin's various VariableStats. """

    def __init__(self, stats_map=None):
        self.stats_map = dict() if stats_map is None else stats_map
        self.is_stale = stats_map is None

    def __getitem__(self, item):
        return self.stats_map.get(item, None)

    def __setitem__(self, key, value):
        if not isinstance(value, VariableStats):
            raise ValueError("value is not of type VariableStats")
        self.stats_map[key] = value

    def __len__(self):
        return self.stats_map.__len__()

    def save(self, path):
        """ Save the plugin stats. """

        result = {varname: self.stats_map[varname].to_dict for varname in self.stats_map.keys()}
        with open(path, 'w') as f:
            json.dump(result, f)
        self.is_stale = False

    @classmethod
    def load(cls, path, plugin_variables, expiration=DEFAULT_CACHE_EXPIRATION):
        """ Load plugin stats. Flags whether the stats are stale or not. """

        with open(path, 'r') as f:
            data = json.load(f)

        # Extract stats for current plugin variables. If any are missing, then cache is stale.
        stats = cls({var: VariableStats.from_dict(data[var]) for var in plugin_variables if var in data})
        if len(stats) < len(plugin_variables):
            stats.is_stale = True

        # Is the cache old?
        maketime = datetime.datetime.fromtimestamp(os.stat(path).st_mtime)
        current = datetime.datetime.now()
        if current - maketime > datetime.timedelta(seconds=expiration):
            stats.is_stale = True

        return stats
