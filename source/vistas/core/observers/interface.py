class Observer:
    def update(self, observable):
        raise NotImplementedError


class Observable:
    observers = set()

    def add_observer(self, observer: Observer):
        self.observers.add(observer)

    def remove_observer(self, observer: Observer):
        if observer in self.observers:
            self.observers.remove(observer)

    def notify_observers(self):
        for obs in self.observers:
            obs.update(self)
