import csv
import datetime
import os
from collections import namedtuple

import numpy

from vistas.core.plugins.data import ArrayDataPlugin, TemporalInfo

Delta = namedtuple('Delta', ['year', 'idu', 'field', 'new_value'])


# Todo - store the start/stop indices for each year, so we can do indexing better.
# This will speed up loading and minimize the amount of IO time we have to spend
class DeltaArray:
    def __init__(self):
        self.deltas = []
        self.base_year = None
        self.year_index_map = {}

    def __len__(self):
        return len(self.deltas)

    def __getitem__(self, item):
        if isinstance(item, slice):
            return self.deltas[item.start:item.start:item.step]
        return self.deltas[item]

    def add_delta(self, index, year, idu, field, new_value):
        if self.base_year is None:
            self.base_year = year

        if year - self.base_year not in self.year_index_map:
            self.year_index_map[year - self.base_year] = index

        self.deltas.append(Delta(year, idu, field, new_value))

    def index_from_year(self, year):
        if year - self.base_year in self.year_index_map:
            return self.year_index_map[year - self.base_year]
        return -1

    def index_range_from_year(self, year):
        return self.index_range_from_year_range(year, year + 1)

    def index_range_from_year_range(self, from_year, to_year):
        count = len(self.deltas)
        end_year = self.deltas[count - 1].year + 1

        if from_year >= end_year:
            from_index_closed = count
        else:
            from_index_closed = self.index_from_year(from_year)

        if to_year >= end_year:
            to_index_open = count
        else:
            to_index_open = self.index_from_year(to_year)

        if to_year < from_year:
            from_index_closed -= 1
            to_index_open -= 1

        return from_index_closed, to_index_open

    @property
    def timestamps(self):
        return sorted([datetime.datetime(year=year + self.base_year, month=1, day=1) for year in self.year_index_map])


class EnvisionDeltaArray(ArrayDataPlugin):

    id = 'envision_delta_reader'
    name = 'Envision Delta Array Data Plugin'
    description = 'Loads ENVISION delta array data from a CSV file.'
    author = 'Conservation Biology Institute'
    version = '1.0'
    extensions = [('csv', 'CSV')]

    data_name = None
    time_info = None
    variables = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.data_name = 'Envision Delta Array'
        self.time_info = TemporalInfo()
        self.delta_array = DeltaArray()
        self.variables = []

    def load_data(self):
        self.variables.clear()
        self.delta_array.deltas.clear()
        self.delta_array.year_index_map.clear()
        self.data_name = self.path.split(os.sep)[-1].split('.')[0]

        with open(self.path, 'r') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                field = row.get('field')
                if field not in self.variables:
                    self.variables.append(field)
                self.delta_array.add_delta(idx, int(row.get('year')), int(row.get('idu')), field,
                                           float(row.get('newValue')))

        timestamps = self.delta_array.timestamps
        if timestamps:
            self.time_info.timestamps = timestamps

    @staticmethod
    def is_valid_file(path):
        return True

    def get_data(self, variable, date=None):
        if date is None:
            return None

        first = self.delta_array.index_from_year(date.year)
        next_year = date + datetime.timedelta(days=365)
        last = self.delta_array.index_from_year(next_year.year)
        if next_year > self.delta_array.timestamps[-1]:
            last = len(self.delta_array)
        if first != -1:
            return [x for x in self.delta_array.deltas[first: last] if x.field == variable]
        else:
            return None

