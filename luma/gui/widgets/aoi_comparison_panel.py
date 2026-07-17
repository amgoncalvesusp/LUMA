"""Interface for comparing several polygonal areas of interest."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget,
)

from luma.core.aoi import AOI
from luma.gui.widgets.aoi_widget import AOIWidget
from luma.i18n.translator import t


class AOIComparisonPanel(QGroupBox):
    """Collect named AOIs and request one comparative analysis."""

    analyze_requested = Signal(list)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(t("aoi_compare.title"), parent)
        self._areas: list[tuple[str, AOI]] = []
        self._aoi_widget = AOIWidget()
        self._list = QListWidget()
        self._list.setMaximumHeight(110)
        self._name = QLabel(t("aoi_compare.instruction"))
        self._name.setWordWrap(True)
        self._add_button = QPushButton(t("aoi_compare.add"))
        self._remove_button = QPushButton(t("aoi_compare.remove"))
        self._analyze_button = QPushButton(t("aoi_compare.analyze"))

        layout = QVBoxLayout(self)
        layout.addWidget(self._aoi_widget)
        layout.addWidget(self._name)
        row = QHBoxLayout()
        row.addWidget(self._add_button)
        row.addWidget(self._remove_button)
        row.addStretch()
        layout.addLayout(row)
        layout.addWidget(self._list)
        layout.addWidget(self._analyze_button)

        self._add_button.clicked.connect(self._add_current)
        self._remove_button.clicked.connect(self._remove_selected)
        self._analyze_button.clicked.connect(self._request_analysis)

    @property
    def areas(self) -> list[tuple[str, AOI]]:
        return list(self._areas)

    def add_aoi(self, aoi: AOI, name: str | None = None) -> None:
        label = name or aoi.name or f"Área {len(self._areas) + 1}"
        self._areas.append((label, aoi))
        self._list.addItem(f"{label} — {aoi.area_km2:.3f} km²")

    def _add_current(self) -> None:
        if self._aoi_widget.aoi is not None:
            self.add_aoi(self._aoi_widget.aoi)

    def _remove_selected(self) -> None:
        index = self._list.currentRow()
        if index < 0:
            return
        self._areas.pop(index)
        self._list.takeItem(index)

    def _request_analysis(self) -> None:
        if len(self._areas) >= 2:
            self.analyze_requested.emit(self.areas)

    def refresh_texts(self) -> None:
        self.setTitle(t("aoi_compare.title"))
        self._name.setText(t("aoi_compare.instruction"))
        self._add_button.setText(t("aoi_compare.add"))
        self._remove_button.setText(t("aoi_compare.remove"))
        self._analyze_button.setText(t("aoi_compare.analyze"))
