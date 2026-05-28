"""Results display — table, metrics, and chart."""

from __future__ import annotations

import math

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QLabel, QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush

from luma.core.stats import AnalysisResult, ClassStats, LandscapeMetrics
from luma.i18n.translator import t
from luma.gui.widgets.help_bubble import HelpBubble


class ResultsTable(QGroupBox):
    """Table showing per-class land-cover statistics."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(t("results.title"), parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        self._info_label = QLabel("")
        self._info_label.setStyleSheet("font-size: 12px; color: #555;")
        layout.addWidget(self._info_label)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "", t("results.category"), t("results.pixels"),
            t("results.area_km2"), t("results.area_ha"), t("results.percentage"),
        ])
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

        self._legend_caption = QLabel(self._build_legend_text())
        self._legend_caption.setWordWrap(True)
        self._legend_caption.setStyleSheet(
            "color: #555; font-size: 11px; padding: 6px 2px; "
            "border-top: 1px solid #eee; margin-top: 4px;"
        )
        layout.addWidget(self._legend_caption)

    def _build_legend_text(self) -> str:
        return (
            f"<b>{t('legend_table.caption')}.</b> "
            f"{t('legend_table.desc_pixels')} "
            f"{t('legend_table.desc_area_km2')} "
            f"{t('legend_table.desc_area_ha')} "
            f"{t('legend_table.desc_percentage')} "
            f"{t('legend_table.desc_num_patches')} "
            f"{t('legend_table.desc_largest_patch')}"
        )

    def update_results(self, result: AnalysisResult) -> None:
        """Populate the table with analysis results."""
        total_km2 = result.total_area_m2 / 1e6
        self._info_label.setText(
            f"{t('results.total_area')}: {total_km2:.2f} km² | "
            f"{t('results.source_label')}: {result.source_name} | "
            f"{t('results.accuracy_label')}: {result.source_accuracy}"
        )

        stats = result.class_stats
        self._table.setRowCount(len(stats))
        for row, cs in enumerate(stats):
            # Color swatch
            color_item = QTableWidgetItem("")
            color_item.setBackground(QBrush(QColor(cs.color)))
            self._table.setItem(row, 0, color_item)

            self._table.setItem(row, 1, QTableWidgetItem(cs.class_name))
            self._table.setItem(
                row, 2, QTableWidgetItem(f"{cs.pixel_count:,}")
            )
            area_km2 = cs.area_m2 / 1e6
            area_ha = cs.area_m2 / 10_000
            self._table.setItem(row, 3, QTableWidgetItem(f"{area_km2:.4f}"))
            self._table.setItem(row, 4, QTableWidgetItem(f"{area_ha:.2f}"))

            pct_item = QTableWidgetItem(f"{cs.percentage:.1f}%")
            pct_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self._table.setItem(row, 5, pct_item)

        self._table.resizeColumnsToContents()
        self._table.setColumnWidth(0, 24)

    def clear(self) -> None:
        self._table.setRowCount(0)
        self._info_label.setText("")

    def refresh_texts(self) -> None:
        self.setTitle(t("results.title"))
        self._table.setHorizontalHeaderLabels([
            "", t("results.category"), t("results.pixels"),
            t("results.area_km2"), t("results.area_ha"), t("results.percentage"),
        ])
        self._legend_caption.setText(self._build_legend_text())


class MetricsPanel(QGroupBox):
    """Panel showing landscape-level metrics with help bubbles."""

    METRICS_DEFS = [
        ("shannon", "metrics.shannon", "tips.shannon"),
        ("simpson", "metrics.simpson", "tips.simpson"),
        ("dominance", "metrics.dominance", "tips.dominance"),
        ("evenness", "metrics.evenness", "tips.evenness"),
        ("total_patches", "metrics.total_patches", "tips.patches"),
        ("patch_density", "metrics.patch_density", "tips.patch_density"),
        ("lpi", "metrics.lpi", "tips.lpi"),
        ("edge_density", "metrics.edge_density", "tips.edge_density"),
        ("mesh_size", "metrics.mesh_size", "tips.mesh_size"),
        ("aggregation_index", "metrics.aggregation_index", "tips.aggregation_index"),
        ("contagion", "metrics.contagion", "tips.contagion"),
        ("mean_shape_index", "metrics.mean_shape_index", "tips.mean_shape_index"),
        ("largest_patch_area", "metrics.largest_patch_area", "tips.largest_patch_area"),
        ("smallest_patch_area", "metrics.smallest_patch_area", "tips.smallest_patch_area"),
        ("mean_patch_area", "metrics.mean_patch_area", "tips.mean_patch_area"),
        ("isa_index", "metrics.isa_index", "tips.isa_index"),
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(t("metrics.title"), parent)
        self._labels: dict[str, QLabel] = {}
        self._name_labels: dict[str, QLabel] = {}
        self._help_bubbles: dict[str, HelpBubble] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        grid = QGridLayout(self)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(2)
        grid.setContentsMargins(6, 4, 6, 4)
        for row, (key, label_key, tip_key) in enumerate(self.METRICS_DEFS):
            lbl = QLabel(t(label_key) + ":")
            lbl.setStyleSheet("font-weight: bold; font-size: 10px;")
            val = QLabel("—")
            val.setStyleSheet("font-size: 10px;")
            val.setMinimumWidth(70)
            bubble = HelpBubble(t(tip_key))
            self._labels[key] = val
            self._name_labels[key] = lbl
            self._help_bubbles[key] = bubble
            grid.addWidget(lbl, row, 0)
            grid.addWidget(val, row, 1)
            grid.addWidget(bubble, row, 2)

    def update_metrics(self, m: LandscapeMetrics, pixel_area_m2: float = 0.0) -> None:
        self._labels["shannon"].setText(f"{m.shannon_diversity:.4f}")
        self._labels["simpson"].setText(f"{m.simpson_diversity:.4f}")
        self._labels["dominance"].setText(f"{m.dominance:.4f}")
        self._labels["evenness"].setText(f"{m.evenness:.4f}")
        self._labels["total_patches"].setText(f"{m.total_patches:,}")
        self._labels["patch_density"].setText(f"{m.patch_density:.2f}")
        self._labels["lpi"].setText(f"{m.largest_patch_index:.2f}%")
        self._labels["edge_density"].setText(f"{m.edge_density:.2f}")
        self._labels["mesh_size"].setText(f"{m.effective_mesh_size:,.2f}")
        self._labels["aggregation_index"].setText(f"{m.aggregation_index:.2f}%")
        self._labels["contagion"].setText(f"{m.contagion:.2f}%")
        self._labels["mean_shape_index"].setText(f"{m.mean_shape_index:.4f}")
        # Convert m² -> ha for display
        self._labels["largest_patch_area"].setText(f"{m.largest_patch_area_m2 / 10_000:,.2f}")
        self._labels["mean_patch_area"].setText(f"{m.mean_patch_area_m2 / 10_000:,.2f}")

        # Smallest patch — warn if it equals ~1 pixel (possible artifact)
        sp_ha = m.smallest_patch_area_m2 / 10_000
        sp_lbl = self._labels["smallest_patch_area"]
        sp_lbl.setText(f"{sp_ha:,.4f}")
        if pixel_area_m2 > 0 and m.smallest_patch_area_m2 <= pixel_area_m2 * 1.05:
            sp_lbl.setStyleSheet("color: #e67e22; font-weight: bold; font-size: 10px;")
            pixel_side = math.sqrt(pixel_area_m2)
            self._help_bubbles["smallest_patch_area"].set_tip(
                t("tips.smallest_patch_area") + "\n\n" +
                t("tips.smallest_patch_pixel_bias", pixel_m=pixel_side)
            )
        else:
            sp_lbl.setStyleSheet("font-size: 10px;")
            self._help_bubbles["smallest_patch_area"].set_tip(t("tips.smallest_patch_area"))

        # ISA index with Walsh classification
        isa = m.isa_index
        if isa < 2:
            isa_cls = t("metrics.isa_ref")
        elif isa < 10:
            isa_cls = t("metrics.isa_sensitive")
        elif isa < 25:
            isa_cls = t("metrics.isa_impacted")
        else:
            isa_cls = t("metrics.isa_severe")
        self._labels["isa_index"].setText(f"{isa:.1f}% — {isa_cls}")

    def clear(self) -> None:
        for lbl in self._labels.values():
            lbl.setText("—")

    def refresh_texts(self) -> None:
        self.setTitle(t("metrics.title"))
        for key, label_key, tip_key in self.METRICS_DEFS:
            self._name_labels[key].setText(t(label_key) + ":")
            self._help_bubbles[key].set_tip(t(tip_key))


class WarningsPanel(QWidget):
    """Display data quality warnings."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._label = QLabel("")
        self._label.setWordWrap(True)
        self._label.setStyleSheet(
            "background: #fff3cd; color: #856404; padding: 8px; "
            "border-radius: 4px; font-size: 12px;"
        )
        self._label.setVisible(False)
        layout.addWidget(self._label)

    def update_warnings(self, warnings: list[str], total_pixels: int) -> None:
        if not warnings:
            self._label.setVisible(False)
            return
        texts = []
        for w in warnings:
            key = f"warnings.{w}"
            texts.append(t(key, n=total_pixels))
        self._label.setText("\n\n".join(texts))
        self._label.setVisible(True)

    def clear(self) -> None:
        self._label.setVisible(False)
