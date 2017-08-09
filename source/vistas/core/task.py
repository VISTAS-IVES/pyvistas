from threading import RLock


class Task:
    """ Abstract class for handling task management. """

    STOPPED = 'stopped'
    RUNNING = 'running'
    INDETERMINATE = 'indeterminate'
    COMPLETE = 'complete'
    SHOULD_STOP = 'should_stop'

    tasks = []

    def __init__(self, name, description=None, target=100, progress=0):
        self.name = name
        self.description = description
        self._target = target
        self._progress = progress
        self._status = self.STOPPED

        self.lock = RLock()

        Task.tasks.append(self)

    @property
    def stopped(self):
        return self._status == self.STOPPED

    @property
    def running(self):
        return self._status == self.RUNNING

    @property
    def indeterminate(self):
        return self._status == self.INDETERMINATE

    @property
    def complete(self):
        return self._status == self.COMPLETE

    @property
    def should_stop(self):
        return self._status == self.SHOULD_STOP

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

        if self.complete:
            Task.tasks.remove(self)

    @property
    def target(self):
        with self.lock:
            return self._target

    @target.setter
    def target(self, value):
        with self.lock:
            self._target = value

    @property
    def progress(self):
        with self.lock:
            return self._progress

    @progress.setter
    def progress(self, value):
        with self.lock:
            self._progress = value

    @property
    def percent(self):
        with self.lock:
            return int(self._progress / self._target * 100)

    def inc_target(self, increment=1):
        with self.lock:
            self._target += increment

    def inc_progress(self, increment=1):
        with self.lock:
            self._progress += increment
