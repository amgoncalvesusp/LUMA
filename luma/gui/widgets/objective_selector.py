"""Beginner-friendly objective selector for the main workflow."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QGroupBox, QLabel, QVBoxLayout, QWidget

from luma.i18n.translator import t


class ObjectiveSelector(QGroupBox):
    """Translate a research question into one of LUMA's analysis tabs."""

    objective_changed = Signal(str)
    objectives = ["single", "temporal", "compare", "compare_aois"]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(t("objective.title"), parent)
        layout = QVBoxLayout(self)
        self._hint = QLabel(t("objective.hint"))
        self._hint.setWordWrap(True)
        self._combo = QComboBox()
        self._populate()
        layout.addWidget(self._hint)
        layout.addWidget(self._combo)
        self._combo.currentIndexChanged.connect(self._emit_current)

    @property
    def selected_objective(self) -> str:
        return str(self._combo.currentData())

    def _populate(self) -> None:
        self._combo.clear()
        for key in self.objectives:
            self._combo.addItem(t(f"objective.{key}"), userData=key)

    def _emit_current(self) -> None:
        self.objective_changed.emit(self.selected_objective)

    def set_objective(self, objective: str) -> None:
        if objective not in self.objectives:
            return
        self._combo.blockSignals(True)
        self._combo.setCurrentIndex(self.objectives.index(objective))
        self._combo.blockSignals(False)

    def refresh_texts(self) -> None:
        self.setTitle(t("objective.title"))
        self._hint.setText(t("objective.hint"))
        current = self.selected_objective
        self._populate()
        index = self.objectives.index(current) if current in self.objectives else 0
        self._combo.setCurrentIndex(index)
