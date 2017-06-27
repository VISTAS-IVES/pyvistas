import os
import csv
import numpy
import datetime

from vistas.core.plugins.data import ArrayDataPlugin, TemporalInfo, VariableStats


class CSVDataPlugin(ArrayDataPlugin):

    id = 'csv_reader'
    name = 'CSV Data Plugin'
    description = 'Loads (time-optional) numerical data from a CSV file.'
    author = 'Conservation Biology Institute'
    extensions = [('csv', 'CSV')]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._temporal_info = TemporalInfo()
        self._stats = {}
        self._num_values = 0
        self._attributes = {}

    def load_data(self):
        with open(self.path, 'r') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

            self._attributes = {field: [] for field in fieldnames}
            for row in reader:
                for attr in self._attributes:
                    self._attributes[attr].append(float(row[attr]))

            # VELMA Table Plugin specifically has these fields. Otherwise, it's a normal csv.
            if {'Year', 'Day'} < set(fieldnames):
                years = self._attributes.pop('Year')
                days = self._attributes.pop('Day')
                self._temporal_info.timestamps = [
                    datetime.datetime(int(years[i]), 1, 1) + datetime.timedelta(int(days[i]) - 1) for i in range(len(years))
                ]

            for attr, data in self._attributes.items():
                self._attributes[attr] = numpy.array(data, dtype=numpy.float32)

    @property
    def data_name(self):
        return self.path.split(os.sep)[-1].split('.')[0]

    @property
    def time_info(self):
        return self._temporal_info

    def variable_stats(self, variable):
        return self._stats[variable]

    @property
    def variables(self):
        return list(self._attributes)

    @staticmethod
    def is_valid_file(path):
        with open(path, 'r') as f:
            try:
                reader = csv.reader(f)
                length = 0
                for i, row in enumerate(reader):
                    if i == 0:
                        length = len(row)
                        continue
                    if len(row) != length:
                        return False
            except csv.Error:
                return False
        return True

    def calculate_stats(self):
        for variable in self.variables:
            var_data = self._attributes[variable]
            self._stats[variable] = VariableStats(var_data.min(), var_data.max())

    def get_data(self, variable):
        return self._attributes[variable]
