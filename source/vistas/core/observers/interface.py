class Observer:
    def update(self, observable):
        raise NotImplementedError("Implemented by subclasses")


class Observable:
    observers = []

    def add_observer(self, observer: Observer):
        self.observers.append(observer)

    def delete_observer(self, observer: Observer):
        if observer in self.observers:
            self.observers.remove(observer)

    def notify_observers(self):
        for obs in self.observers:
            obs.update(self)
