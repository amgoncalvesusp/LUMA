"""Legend preview dialog showing classes with color swatches."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap, QPainter
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget,
)

from luma.i18n.translator import t
from luma.sources.catalog import load_legend


def _color_swatch(hex_color: str, size: int = 18) -> QPixmap:
    """Return a small rounded pixmap filled with the given hex color."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = QColor(hex_color) if hex_color else QColor("#888888")
    if not color.isValid():
        color = QColor("#888888")
    painter.setBrush(color)
    painter.setPen(QColor("#2c3e50"))
    painter.drawRoundedRect(0, 0, size - 1, size - 1, 3, 3)
    painter.end()
    return pm


class LegendPreviewDialog(QDialog):
    """Modal dialog that displays a legend's classes with color swatches."""

    def __init__(self, legend_key: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._legend_key = legend_key
        try:
            legend = load_legend(legend_key)
        except FileNotFoundError:
            legend = {"name": legend_key, "classes": {}}

        name = legend.get("name", legend_key)
        classes = legend.get("classes", {})

        self.setWindowTitle(t("input.legend_preview_title", name=name))
        self.setMinimumSize(420, 360)

        layout = QVBoxLayout(self)

        # Header with legend metadata
        meta_bits = []
        if legend.get("resolution"):
            meta_bits.append(str(legend["resolution"]))
        if legend.get("coverage"):
            meta_bits.append(str(legend["coverage"]))
        if meta_bits:
            hdr = QLabel(" • ".join(meta_bits))
            hdr.setStyleSheet("color: #555; font-size: 11px; padding-bottom: 4px;")
            layout.addWidget(hdr)

        # Classes table
        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels([
            t("input.legend_col_id"),
            t("input.legend_col_color"),
            t("input.legend_col_name"),
        ])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setRowCount(len(classes))

        for row, (cls_id, info) in enumerate(sorted(classes.items(), key=lambda kv: int(kv[0]))):
            id_item = QTableWidgetItem(str(cls_id))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 0, id_item)

            color = (info or {}).get("color", "#888888")
            color_item = QTableWidgetItem("  " + color)
            color_item.setIcon(_color_swatch(color))
            self._table.setItem(row, 1, color_item)

            name_item = QTableWidgetItem((info or {}).get("name", f"Class {cls_id}"))
            self._table.setItem(row, 2, name_item)

        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch,
        )
        layout.addWidget(self._table, 1)

        # Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_close = QPushButton(t("input.legend_close"))
        self._btn_close.clicked.connect(self.accept)
        self._btn_close.setDefault(True)
        btn_row.addWidget(self._btn_close)
        layout.addLayout(btn_row)
