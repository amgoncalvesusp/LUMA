"""Reusable Qt worker for analyses that may read large remote rasters."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Signal


class TaskWorker(QObject):
    """Execute a pure callable in a ``QThread`` and return value or exception."""

    finished = Signal(object)
    progress = Signal(str)

    def __init__(self, task: Callable[[], object]):
        super().__init__()
        self._task = task

    def run(self) -> None:
        try:
            self.finished.emit(self._task())
        except Exception as exc:  # callbacks render a user-facing message
            self.finished.emit(exc)
