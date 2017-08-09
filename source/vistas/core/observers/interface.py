class Observer:
    """ An abstract class for performing updates initiated by an Observable. """

    def update(self, observable):
        raise NotImplementedError


class Observable:
    """ A class for registering Observers to be updated. """

    observers = []

    def add_observer(self, observer: Observer):
        self.observers.append(observer)

    def remove_observer(self, observer: Observer):
        if observer in self.observers:
            self.observers.remove(observer)

    def notify_observers(self):
        for obs in self.observers:
            obs.update(self)
