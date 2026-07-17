from luma.gui.task_runner import TaskWorker


def test_task_worker_returns_callable_value():
    worker = TaskWorker(lambda: {"ok": True})
    values = []
    worker.finished.connect(values.append)

    worker.run()

    assert values == [{"ok": True}]


def test_task_worker_returns_exception_without_raising():
    worker = TaskWorker(lambda: 1 / 0)
    values = []
    worker.finished.connect(values.append)

    worker.run()

    assert len(values) == 1
    assert isinstance(values[0], ZeroDivisionError)
