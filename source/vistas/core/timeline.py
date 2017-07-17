import datetime
from bisect import insort

from vistas.core.utils import DatetimeEncoder, DatetimeDecoder
from vistas.ui.events import TimelineEvent
from vistas.ui.utils import post_timeline_change


class Timeline:
    _global_timeline = None

    @classmethod
    def app(cls):
        """ Global timeline """

        if cls._global_timeline is None:
            cls._global_timeline = Timeline()

        return cls._global_timeline

    def __init__(self, start=None, end=None, current=None):

        init_time = datetime.datetime.fromtimestamp(0)

        self._start = init_time if start is None else start
        self._end = init_time if end is None else end
        self._current = init_time if current is None else current
        self._min_step = datetime.timedelta(days=1)
        self._timestamps = []
        self._current_idx = 0

        # filter settings
        self.use_filter = False
        self.filter_start = start
        self.filter_end = end
        self.filter_interval = self._min_step

        self.nearest_step()

    def nearest_step(self):
        low_idx = 0
        high_idx = len(self.timestamps) - 1

        start = self.filter_start if self.use_filter else self._start
        end = self.filter_end if self.use_filter else self._end

        if self._current == end:
            self._current_idx = high_idx
            return False

        if self._current < start:
            self._current = start
            self._current_idx = low_idx
            return True

        if self._current > end:
            self._current = end
            self._current_idx = high_idx
            return True

        self._current_idx = self.timestamps.index(self._current)
        return False

    @property
    def enabled(self):
        return self.start != self.end

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, start: datetime.datetime):
        self._start = start
        post_timeline_change(self._current, TimelineEvent.ATTR_CHANGED)
        if self.nearest_step():
            post_timeline_change(self._current, TimelineEvent.VALUE_CHANGED)

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, end):
        self._end = end
        post_timeline_change(self._current, TimelineEvent.ATTR_CHANGED)
        if self.nearest_step():
            post_timeline_change(self._current, TimelineEvent.VALUE_CHANGED)

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, current: datetime.datetime):
        if self.enabled:
            self._current = current
            self.nearest_step()
            post_timeline_change(self._current, TimelineEvent.VALUE_CHANGED)

    @property
    def min_step(self):
        return self._min_step

    @property
    def timestamps(self):
        if self.use_filter:
            filtered_steps = []
            step = self.filter_start
            while step <= self.filter_end:
                if step in self._timestamps:
                    filtered_steps.append(step)
                step = step + self.filter_interval
            return filtered_steps
        return self._timestamps

    @property
    def num_timestamps(self):
        return len(self.timestamps)

    @property
    def time_format(self):
        _format = "%B %d, %Y"

        hour, minute, second = [False] * 3
        for t in self.timestamps:
            hour = not hour and t.hour > 0
            minute = not minute and t.minute > 0
            second = not second and t.second > 0
            if hour and minute and second:
                break

        if hour or minute or second:
            _format = _format + " %H:%M"
            if second:
                _format = _format + ":%S"

        return _format

    def reset(self):
        zero = datetime.datetime.fromtimestamp(0)
        self._timestamps = []
        self._start, self._end, self._current = [zero] * 3
        self.filter_start, self.filter_end = [zero] * 2
        self._min_step, self.filter_interval = [datetime.timedelta(days=1)] * 2
        self.use_filter = False

    def add_timestamp(self, timestamp: datetime.datetime):
        if timestamp not in self._timestamps:
            insort(self._timestamps, timestamp)     # unique and sorted

            # recalculate smallest timedelta
            self._min_step = self._timestamps[-1] - self._timestamps[0]
            for i in range(len(self._timestamps) - 1):
                diff = self._timestamps[i + 1] - self._timestamps[i]
                if diff < self._min_step:
                    self._min_step = diff

        # Update filter ranges
        if not self.use_filter:
            self.filter_start = self.start
            self.filter_end = self.end
            self.filter_interval = self._min_step

    def index_at_time(self, time: datetime.datetime):
        return self.timestamps.index(time)

    @property
    def current_index(self):
        return self._current_idx

    def time_at_index(self, index):
        length = self.num_timestamps
        if index < 0:
            index = 0
        elif index >= length:
            index = length - 1
        return self.timestamps[index]

    def forward(self, steps=1):
        index = self.current_index + steps
        length = self.num_timestamps
        if index >= length:
            index = length - 1
        elif index < 0:
            index = 0
        self._current_idx = index
        self._current = self.timestamps[self._current_idx]
        post_timeline_change(self._current, TimelineEvent.VALUE_CHANGED)

    def back(self, steps=1):
        self.forward(steps * -1)

    def serialize_filter(self):
        if not self.use_filter:
            return None

        e = DatetimeEncoder()
        return {
            'filter_start': e.default(self.filter_start),
            'filter_end': e.default(self.filter_end),
            'filter_interval': e.default(self.filter_interval)
        }

    def load_filter(self, data):
        if data is not None:
            d = DatetimeDecoder()
            self.use_filter = True
            self.filter_start = d.dict_to_object(data['filter_start'])
            self.filter_end = d.dict_to_object(data['filter_end'])
            self.filter_interval = d.dict_to_object(data['filter_interval'])
