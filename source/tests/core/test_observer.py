from copy import copy
from pytest import fixture

from vistas.core.observers.interface import *


@fixture(scope='session')
def observer():
    class TestObserver(Observer):
        def __init__(self):
            self.x = 5

        def update(self, observable):
            self.x **= 2
    return TestObserver()


def test_add_observer(observer):
    obs = Observable()
    obs.add_observer(observer)
    assert len(obs.observers) == 1
    obs.add_observer(observer)
    assert len(obs.observers) == 1


def test_cls_observers():
    assert len(Observable.observers) == 1


def test_notify_observers(observer):
    obs = Observable()
    obs.notify_observers()
    assert observer.x == 25


def test_remove_observer(observer):
    observer2 = copy(observer)
    obs = Observable()
    obs.add_observer(observer2)
    assert len(obs.observers) == 2

    # Test removal
    obs.remove_observer(observer)
    assert len(obs.observers) == 1

    # Test unique removal
    obs.remove_observer(observer)
    assert len(obs.observers) == 1

    obs.remove_observer(observer2)
    assert len(obs.observers) == 0
