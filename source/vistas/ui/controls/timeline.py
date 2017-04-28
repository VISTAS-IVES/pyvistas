import datetime
from bisect import insort


class TimelineFilter:
    pass # Todo: implement


class Timeline:
    _global_timeline = None

    @classmethod
    def app(cls):
        """ Global timeline """

        if cls._global_timeline is None:
            cls._global_timeline = Timeline()

        return cls._global_timeline

    def __init__(self, start_time=None, end_time=None, current_time=None):

        self._start_time = start_time
        self._end_time = end_time
        self._current_time = current_time
        self._min_step = None
        self._timestamps = []

        # Todo: implement TimelineFilter
        # self._filtered_timestamps = []  # potentially unneeded, since we can filter on the fly now
        # self._use_filter = False

    @property
    def timestamps(self):
        # return self._filtered_timestamps if self._use_filter else self._timestamps
        return self._timestamps

    @property
    def num_timestamps(self):
        return len(self._timestamps)

    @property
    def start_time(self):
        return self._start_time

    @start_time.setter
    def start_time(self, value: datetime.datetime):
        self._start_time = value
        # Todo: TimelineEvent?

    @property
    def end_time(self):
        return self._end_time

    @end_time.setter
    def end_time(self, value):
        self._end_time = value
        # Todo: TimelineEvent?

    @property
    def current_time(self):
        return self._current_time

    @current_time.setter
    def current_time(self, value: datetime.datetime):
        if value not in self._timestamps:
            if value > self._timestamps[-1]:
                value = self._timestamps[-1]
            elif value < self._timestamps[0]:
                value = self._timestamps[0]
            else:
                # Go to nearest floor step
                value = list(filter(lambda x: x > value, self._timestamps))[0]
        self._current_time = value
        # Todo: TimelineEvent?

    @property
    def min_step(self):
        return self._min_step

    def reset(self):
        self._timestamps = []
        self._start_time, self._end_time, self._current_time = [datetime.datetime.fromtimestamp(0)] * 3

    def add_timestamp(self, timestamp: datetime.datetime):
        if timestamp not in self._timestamps:
            if timestamp > self._timestamps[-1]:
                self.end_time = timestamp
            elif timestamp < self._timestamps[0]:
                self.start_time = timestamp
            insort(self._timestamps, timestamp)     # unique and sorted

            # recalculate smallest timedelta
            self._min_step = self._timestamps[-1] - self._timestamps[0]
            for i in range(len(self._timestamps) - 1):
                diff = self._timestamps[i+1] - self._timestamps[i+1]
                self._min_step = diff if diff < self._min_step else self._min_step

    def index_at_time(self, time: datetime.datetime):
        return self._timestamps.index(time)

    @property
    def current_index(self):
        return self.index_at_time(self._current_time)

    def time_at_index(self, index):
        return self.timestamps[index]
