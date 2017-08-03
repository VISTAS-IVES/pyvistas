from pytest import fixture

from vistas.core.task import Task


@fixture(scope='function')
def task_cls():
    yield Task
    Task.tasks = []


def test_create(task_cls):
    task = task_cls('Task')
    assert task_cls.tasks == [task]


def test_task_list(task_cls):
    task = task_cls('Task 1')
    task2 = task_cls('Task 2')
    assert task_cls.tasks == [task, task2]

    # Make sure setting status other than COMPLETE doesn't remove task from list
    for status in (task.STOPPED, task.RUNNING, task.INDETERMINATE, task.SHOULD_STOP):
        task.status = status
        assert task_cls.tasks == [task, task2]

    task.status = task.COMPLETE
    assert task_cls.tasks == [task2]


def test_percent(task_cls):
    task = task_cls('Task')
    task.target = 200
    task.progress = 50

    assert task.percent == 25


def test_inc(task_cls):
    task = task_cls('Task')
    task.target = 100
    task.progress = 50
    task.inc_target(10)
    assert task.target == 110

    task.inc_progress(10)
    assert task.progress == 60
