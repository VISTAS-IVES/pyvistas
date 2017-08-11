import time
import hashlib
import json
import os


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
    def from_dict(cls, data):
        d = data.copy()
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

    def save(self, save_path, data_path):
        """ Save the plugin stats. """

        result = {
            'stats': {varname: self.stats_map[varname].to_dict for varname in self.stats_map.keys()},
            'last_modified': time.time(),
            'checksum': compute_file_checksum(data_path)
        }
        with open(save_path, 'w') as f:
            json.dump(result, f)
        self.is_stale = False

    @classmethod
    def load(cls, load_path, data_path, plugin_variables):
        """ Load plugin stats. Flags whether the stats are stale or not. """

        with open(load_path, 'r') as f:
            data = json.load(f)

        stored = data.get('stats')
        stats = cls({var: VariableStats.from_dict(stored.get(var)) for var in plugin_variables if var in stored})

        # Check if the cache is stale - first by recorded data_path's modify time, and then by checksum
        if data.get('last_modified') < os.path.getmtime(data_path):
            if data.get('checksum') != compute_file_checksum(data_path):
                stats.is_stale = True

        return stats


def compute_file_checksum(path):
    """ Compute a SHA1 checksum for a file. """

    with open(path, 'rb') as f:
        checksum = hashlib.sha1(f.read()).hexdigest()
    return checksum
