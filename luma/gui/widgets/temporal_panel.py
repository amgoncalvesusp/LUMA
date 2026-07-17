"""Temporal analysis panel — transition matrix (2 dates) and multi-year time series."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFileDialog, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QRadioButton, QButtonGroup, QStackedWidget,
    QFrame, QScrollArea,
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QColor, QBrush

from luma.i18n.translator import t
from luma.gui.widgets.help_bubble import HelpBubble


# ── Helper: a single (year, file) row for multi-year mode ─────────────────────

class _YearFileRow(QWidget):
    """One row in the multi-year input: year spinner + file picker + remove."""

    removed = Signal(object)  # emits self

    def __init__(self, index: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.index = index
        self._file = ""

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)

        self._spin = QSpinBox()
        self._spin.setRange(1985, 2030)
        self._spin.setValue(2000 + index * 5)
        self._spin.setMinimumWidth(80)
        self._spin.setStyleSheet("QSpinBox { font-size: 13px; padding: 2px 4px; }")
        row.addWidget(QLabel(t("input.year") + ":"))
        row.addWidget(self._spin)

        self._btn_file = QPushButton(t("temporal.file_select"))
        self._btn_file.clicked.connect(self._pick_file)
        row.addWidget(self._btn_file)

        self._lbl_file = QLabel(t("temporal.no_file"))
        self._lbl_file.setStyleSheet("color: #666; font-size: 11px;")
        row.addWidget(self._lbl_file, stretch=1)

        btn_rm = QPushButton("✕")
        btn_rm.setFixedWidth(28)
        btn_rm.setStyleSheet("color: #c0392b; font-weight: bold;")
        btn_rm.clicked.connect(lambda: self.removed.emit(self))
        row.addWidget(btn_rm)

    def _pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("input.select_file"), "",
            "GeoTIFF (*.tif *.tiff);;All Files (*)",
        )
        if path:
            self._file = path
            self._lbl_file.setText(Path(path).name)

    def get_year_file(self) -> tuple[int, str]:
        return self._spin.value(), self._file

    def refresh_texts(self) -> None:
        self._btn_file.setText(t("temporal.file_select"))
        if not self._file:
            self._lbl_file.setText(t("temporal.no_file"))


# ── Main panel ─────────────────────────────────────────────────────────────────

class TemporalPanel(QGroupBox):
    """Panel for multi-temporal analysis.

    Two modes:
    • Transition (2 dates) — existing transition matrix.
    • Time series (N years) — longitudinal coverage table.
    """

    analyze_requested = Signal(str, str, int, int)   # file1, file2, year1, year2
    analyze_multi_requested = Signal(list)             # list[(year, file), ...]

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt API
        """Allow the inputs to fit without horizontal scrolling on notebooks."""
        return QSize(520, 420)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(t("temporal.title"), parent)
        self._file_t1 = ""
        self._file_t2 = ""
        self._year_rows: list[_YearFileRow] = []
        self._setup_ui()

    # ── Setup ──────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ── Mode selector ──────────────────────────────────────────────────
        mode_row = QHBoxLayout()
        self._rb_transition = QRadioButton(t("temporal.mode_transition"))
        self._rb_series = QRadioButton(t("temporal.mode_series"))
        self._rb_transition.setChecked(True)
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._rb_transition, 0)
        self._mode_group.addButton(self._rb_series, 1)
        self._mode_group.idClicked.connect(self._on_mode_changed)
        mode_row.addWidget(self._rb_transition)
        mode_row.addWidget(self._rb_series)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #ddd;")
        layout.addWidget(sep)

        # ── Stacked input area ─────────────────────────────────────────────
        self._stack = QStackedWidget()

        # -- Mode 0: transition (2 dates) --
        page0 = QWidget()
        p0_lay = QVBoxLayout(page0)
        p0_lay.setContentsMargins(0, 0, 0, 0)

        row1 = QHBoxLayout()
        self._lbl_y1 = QLabel(t("temporal.year_from"))
        row1.addWidget(self._lbl_y1)
        self._spin_y1 = QSpinBox()
        self._spin_y1.setRange(1985, 2030)
        self._spin_y1.setValue(2015)
        self._spin_y1.setMinimumWidth(90)
        self._spin_y1.setStyleSheet("QSpinBox { font-size: 14px; padding: 2px 4px; }")
        row1.addWidget(self._spin_y1)
        self._btn_f1 = QPushButton(t("temporal.file_from"))
        self._btn_f1.clicked.connect(lambda: self._pick_file(1))
        row1.addWidget(self._btn_f1)
        self._lbl_f1 = QLabel("")
        self._lbl_f1.setStyleSheet("color: #666; font-size: 11px;")
        row1.addWidget(self._lbl_f1, stretch=1)
        p0_lay.addLayout(row1)

        row2 = QHBoxLayout()
        self._lbl_y2 = QLabel(t("temporal.year_to"))
        row2.addWidget(self._lbl_y2)
        self._spin_y2 = QSpinBox()
        self._spin_y2.setRange(1985, 2030)
        self._spin_y2.setValue(2023)
        self._spin_y2.setMinimumWidth(90)
        self._spin_y2.setStyleSheet("QSpinBox { font-size: 14px; padding: 2px 4px; }")
        row2.addWidget(self._spin_y2)
        self._btn_f2 = QPushButton(t("temporal.file_to"))
        self._btn_f2.clicked.connect(lambda: self._pick_file(2))
        row2.addWidget(self._btn_f2)
        self._lbl_f2 = QLabel("")
        self._lbl_f2.setStyleSheet("color: #666; font-size: 11px;")
        row2.addWidget(self._lbl_f2, stretch=1)
        p0_lay.addLayout(row2)

        btn_row0 = QHBoxLayout()
        self._btn_analyze = QPushButton(t("temporal.analyze_change"))
        self._btn_analyze.setStyleSheet(
            "QPushButton { background: #e67e22; color: white; padding: 6px 20px; "
            "border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #d35400; }"
        )
        self._btn_analyze.clicked.connect(self._on_analyze_transition)
        btn_row0.addWidget(self._btn_analyze)
        self._tip_transition = HelpBubble(t("tips.transition_matrix"))
        btn_row0.addWidget(self._tip_transition)
        btn_row0.addStretch()
        p0_lay.addLayout(btn_row0)
        self._stack.addWidget(page0)

        # -- Mode 1: time series (N years) --
        page1 = QWidget()
        p1_lay = QVBoxLayout(page1)
        p1_lay.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(200)
        self._rows_container_widget = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container_widget)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.addStretch()
        scroll.setWidget(self._rows_container_widget)
        p1_lay.addWidget(scroll)

        btn_row1 = QHBoxLayout()
        self._btn_add_year = QPushButton(t("temporal.add_year"))
        self._btn_add_year.clicked.connect(self._add_year_row)
        btn_row1.addWidget(self._btn_add_year)

        self._btn_analyze_series = QPushButton(t("temporal.analyze_series"))
        self._btn_analyze_series.setStyleSheet(
            "QPushButton { background: #8e44ad; color: white; padding: 6px 20px; "
            "border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #7d3c98; }"
        )
        self._btn_analyze_series.clicked.connect(self._on_analyze_series)
        btn_row1.addWidget(self._btn_analyze_series)
        btn_row1.addStretch()
        p1_lay.addLayout(btn_row1)
        self._stack.addWidget(page1)

        layout.addWidget(self._stack)

        # ── Results area ───────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        self._summary = QTextEdit()
        self._summary.setReadOnly(True)
        self._summary.setMaximumHeight(120)
        self._summary.setStyleSheet("font-size: 12px;")
        layout.addWidget(self._summary)

        # Add two default year rows for series mode
        self._add_year_row()
        self._add_year_row()

    # ── Mode handling ──────────────────────────────────────────────────────

    def _on_mode_changed(self, mode_id: int) -> None:
        self._stack.setCurrentIndex(mode_id)
        self._table.setRowCount(0)
        self._summary.clear()

    # ── Transition mode (2 dates) ──────────────────────────────────────────

    def _pick_file(self, which: int) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("input.select_file"), "",
            "GeoTIFF (*.tif *.tiff);;All Files (*)",
        )
        if path:
            name = Path(path).name
            if which == 1:
                self._file_t1 = path
                self._lbl_f1.setText(name)
            else:
                self._file_t2 = path
                self._lbl_f2.setText(name)

    def _on_analyze_transition(self) -> None:
        # Empty paths are resolved from a selected remote catalog source.
        if (self._file_t1 and self._file_t2) or (not self._file_t1 and not self._file_t2):
            self.analyze_requested.emit(
                self._file_t1, self._file_t2,
                self._spin_y1.value(), self._spin_y2.value(),
            )

    # ── Series mode (N years) ──────────────────────────────────────────────

    def _add_year_row(self) -> None:
        row = _YearFileRow(len(self._year_rows), self)
        row.removed.connect(self._remove_year_row)
        self._year_rows.append(row)
        # Insert before the stretch
        self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)

    def _remove_year_row(self, row: _YearFileRow) -> None:
        if len(self._year_rows) <= 2:
            return
        self._rows_layout.removeWidget(row)
        row.deleteLater()
        self._year_rows.remove(row)

    def _on_analyze_series(self) -> None:
        values = [r.get_year_file() for r in self._year_rows]
        pairs = ([(yr, "") for yr, _ in values] if not any(fp for _, fp in values)
                 else [(yr, fp) for yr, fp in values if fp])
        if len(pairs) < 2:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", t("temporal.series_need_two"))
            return
        self.analyze_multi_requested.emit(pairs)

    # ── Results: transition matrix ─────────────────────────────────────────

    def update_results(self, transition_data: dict, year1: int = 0, year2: int = 0) -> None:
        """Display transition matrix and summary with % change."""
        matrix = transition_data["matrix"]
        classes = transition_data["classes"]
        legend = transition_data["legend"]

        n = len(classes)
        self._table.setRowCount(n + 1)
        self._table.setColumnCount(n + 1)

        class_names = [legend.get(c, {}).get("name", f"Class {c}") for c in classes]

        y1 = year1 or self._spin_y1.value()
        y2 = year2 or self._spin_y2.value()
        corner_text = t("temporal.matrix_from", year=y1, year2=y2)
        corner_item = QTableWidgetItem(corner_text)
        corner_item.setBackground(QBrush(QColor("#eee")))
        corner_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self._table.setItem(0, 0, corner_item)

        for j, name in enumerate(class_names):
            item = QTableWidgetItem(name)
            item.setBackground(QBrush(QColor("#d6eaf8")))
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._table.setItem(0, j + 1, item)

        for i, name in enumerate(class_names):
            item = QTableWidgetItem(name)
            item.setBackground(QBrush(QColor("#d6eaf8")))
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._table.setItem(i + 1, 0, item)

        self._table.horizontalHeader().setVisible(False)
        self._table.verticalHeader().setVisible(False)

        for i, c1 in enumerate(classes):
            for j, c2 in enumerate(classes):
                val = matrix[c1].get(c2, 0) / 1e6
                item = QTableWidgetItem(f"{val:.2f}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if i == j:
                    item.setBackground(QBrush(QColor("#d5f5e3")))
                elif val > 0:
                    item.setBackground(QBrush(QColor("#fadbd8")))
                self._table.setItem(i + 1, j + 1, item)

        self._table.resizeColumnsToContents()

        # Summary with % change
        persistence = transition_data["persistence"]
        net = transition_data["net_change"]
        area_t1 = transition_data.get("area_t1", {})
        lines = [
            f"{t('temporal.persistence')}: {persistence:.1f}%",
            "",
            f"{t('temporal.net_change')} (km²  |  %):",
        ]
        for c in classes:
            name = legend.get(c, {}).get("name", f"Class {c}")
            change_km2 = net.get(c, 0) / 1e6
            a_t1 = area_t1.get(c, 0) / 1e6
            sign = "+" if change_km2 >= 0 else ""
            if a_t1 > 0:
                pct = change_km2 / a_t1 * 100
                pct_sign = "+" if pct >= 0 else ""
                lines.append(f"  {name}: {sign}{change_km2:.2f} km²  ({pct_sign}{pct:.1f}%)")
            else:
                lines.append(f"  {name}: {sign}{change_km2:.2f} km²")

        if "metrics_t1" in transition_data and "metrics_t2" in transition_data:
            isa1 = transition_data["metrics_t1"].isa_index
            isa2 = transition_data["metrics_t2"].isa_index
            delta = isa2 - isa1
            sign = "+" if delta >= 0 else ""
            lines.extend([
                "",
                f"{t('metrics.isa_index')}: {isa1:.1f}% -> {isa2:.1f}% ({sign}{delta:.1f} p.p.)",
            ])

        self._summary.setPlainText("\n".join(lines))

    # ── Results: time series ───────────────────────────────────────────────

    def update_series_results(self, series_data: list[dict]) -> None:
        """Display longitudinal table: rows = classes, cols = years.

        series_data: list of {"year": int, "class_stats": list[ClassStats]}
        sorted by year ascending.
        """
        if not series_data:
            return

        # Collect all class names (preserve order of first appearance)
        all_classes: list[str] = []
        seen: set[str] = set()
        for entry in series_data:
            for cs in entry["class_stats"]:
                if cs.class_name not in seen:
                    all_classes.append(cs.class_name)
                    seen.add(cs.class_name)

        years = [e["year"] for e in series_data]
        has_isa = all("landscape_metrics" in entry for entry in series_data)
        n_rows = len(all_classes) + (1 if has_isa else 0)
        n_cols = len(years) + 1  # +1 for class name column

        self._table.setRowCount(n_rows)
        self._table.setColumnCount(n_cols)
        self._table.horizontalHeader().setVisible(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setHorizontalHeaderLabels([t("results.category")] + [str(y) for y in years])

        for row, cls_name in enumerate(all_classes):
            self._table.setItem(row, 0, QTableWidgetItem(cls_name))
            prev_pct: float | None = None
            for col, entry in enumerate(series_data, 1):
                pct = 0.0
                for cs in entry["class_stats"]:
                    if cs.class_name == cls_name:
                        pct = cs.percentage
                        break
                item = QTableWidgetItem(f"{pct:.1f}%")
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                # Colour coding relative to previous year
                if prev_pct is not None:
                    if pct > prev_pct + 0.5:
                        item.setBackground(QBrush(QColor("#d5f5e3")))
                    elif pct < prev_pct - 0.5:
                        item.setBackground(QBrush(QColor("#fadbd8")))
                self._table.setItem(row, col, item)
                prev_pct = pct

        if has_isa:
            row = len(all_classes)
            self._table.setItem(row, 0, QTableWidgetItem(t("metrics.isa_index")))
            prev_isa: float | None = None
            for col, entry in enumerate(series_data, 1):
                isa = entry["landscape_metrics"].isa_index
                item = QTableWidgetItem(f"{isa:.1f}%")
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if prev_isa is not None:
                    if isa > prev_isa + 0.5:
                        item.setBackground(QBrush(QColor("#d5f5e3")))
                    elif isa < prev_isa - 0.5:
                        item.setBackground(QBrush(QColor("#fadbd8")))
                self._table.setItem(row, col, item)
                prev_isa = isa

        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        # Summary: net change first→last year
        lines = [f"{t('temporal.series_summary')} ({years[0]} → {years[-1]}):"]
        first_map = {cs.class_name: cs.percentage for cs in series_data[0]["class_stats"]}
        last_map = {cs.class_name: cs.percentage for cs in series_data[-1]["class_stats"]}
        if has_isa:
            isa0 = series_data[0]["landscape_metrics"].isa_index
            isa1 = series_data[-1]["landscape_metrics"].isa_index
            delta = isa1 - isa0
            sign = "+" if delta >= 0 else ""
            lines.append(f"  {t('metrics.isa_index')}: {isa0:.1f}% -> {isa1:.1f}%  ({sign}{delta:.1f} p.p.)")
        for cls_name in all_classes:
            p0 = first_map.get(cls_name, 0)
            p1 = last_map.get(cls_name, 0)
            delta = p1 - p0
            sign = "+" if delta >= 0 else ""
            lines.append(f"  {cls_name}: {p0:.1f}% → {p1:.1f}%  ({sign}{delta:.1f} p.p.)")
        self._summary.setPlainText("\n".join(lines))

    # ── i18n refresh ───────────────────────────────────────────────────────

    def refresh_texts(self) -> None:
        self.setTitle(t("temporal.title"))
        self._rb_transition.setText(t("temporal.mode_transition"))
        self._rb_series.setText(t("temporal.mode_series"))
        self._lbl_y1.setText(t("temporal.year_from"))
        self._lbl_y2.setText(t("temporal.year_to"))
        self._btn_f1.setText(t("temporal.file_from"))
        self._btn_f2.setText(t("temporal.file_to"))
        self._btn_analyze.setText(t("temporal.analyze_change"))
        self._tip_transition.set_tip(t("tips.transition_matrix"))
        self._btn_add_year.setText(t("temporal.add_year"))
        self._btn_analyze_series.setText(t("temporal.analyze_series"))
        for row in self._year_rows:
            row.refresh_texts()
