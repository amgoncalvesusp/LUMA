from luma.gui.task_runner import TaskWorker


def test_background_task_keeps_worker_until_callback():
    """The GUI host must retain the worker while a thread is running.

    A local-only ``TaskWorker`` reference is not sufficient in PySide: the
    wrapper may be collected as soon as ``_start_background_task`` returns,
    before the result reaches the UI callback.
    """
    from luma.gui.main_window import MainWindow
    from PySide6.QtWidgets import QApplication
    import time

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    values = []

    assert window._start_background_task(lambda: {"ok": True}, values.append)
    assert window._active_task_worker is not None
    deadline = time.monotonic() + 3
    while not values and time.monotonic() < deadline:
        app.processEvents()
    assert values == [{"ok": True}]
    deadline = time.monotonic() + 3
    while window._active_task_thread is not None and time.monotonic() < deadline:
        app.processEvents()
    assert window._active_task_worker is None
    window.close()


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
