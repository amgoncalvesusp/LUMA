"""Main application window — assembles all panels, handles analysis logic."""

from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QTabWidget, QStatusBar, QMenuBar, QMessageBox, QFileDialog,
    QSplitter, QLabel, QComboBox, QApplication, QProgressDialog,
    QScrollArea,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QAction

import luma
from luma.i18n.translator import t, init as i18n_init, set_language, AVAILABLE_LANGUAGES, get_language
from luma.gui.widgets.coord_input import LatitudeInput, LongitudeInput, RadiusInput
from luma.gui.widgets.source_selector import SourceSelector
from luma.gui.widgets.map_viewer import MapViewer
from luma.gui.widgets.results_table import ResultsTable, MetricsPanel, WarningsPanel
from luma.gui.widgets.help_bubble import HelpBubble, labeled_input_with_help
from luma.gui.widgets.temporal_panel import TemporalPanel
from luma.gui.widgets.compare_panel import ComparePanel
from luma.gui.dialogs.about import AboutDialog
from luma.gui.dialogs.settings import SettingsDialog
from luma.core.raster import clip_raster_to_buffer
from luma.core.stats import (
    compute_class_statistics, compute_landscape_metrics,
    generate_quality_warnings, AnalysisResult, compute_transition_matrix,
)
from luma.core.buffer import buffer_geojson, buffer_area_km2
from luma.sources.catalog import load_legend_classes, get_source, load_legend, resolve_remote_url


# ---------------------------------------------------------------------------
# Worker for background analysis
# ---------------------------------------------------------------------------
class AnalysisWorker(QObject):
    finished = Signal(object)  # AnalysisResult or Exception
    progress = Signal(str)

    def __init__(self, source_path: str, lon: float, lat: float,
                 radius_m: float, legend_key: str):
        super().__init__()
        self.source_path = source_path
        self.lon = lon
        self.lat = lat
        self.radius_m = radius_m
        self.legend_key = legend_key

    def run(self) -> None:
        try:
            self.progress.emit(t("status.analyzing"))
            legend_classes = load_legend_classes(self.legend_key)
            legend_meta = load_legend(self.legend_key)

            raster = clip_raster_to_buffer(
                self.source_path, self.lon, self.lat, self.radius_m
            )

            class_stats = compute_class_statistics(
                raster.data, raster.valid_mask, raster.pixel_area_m2, legend_classes
            )
            landscape = compute_landscape_metrics(
                class_stats, raster.data, raster.valid_mask, raster.pixel_area_m2
            )
            warnings = generate_quality_warnings(
                raster.total_pixels, raster.pixel_area_m2, self.radius_m
            )

            result = AnalysisResult(
                class_stats=class_stats,
                landscape_metrics=landscape,
                total_area_m2=raster.total_pixels * raster.pixel_area_m2,
                total_valid_pixels=raster.total_pixels,
                pixel_area_m2=raster.pixel_area_m2,
                quality_warnings=warnings,
                source_name=legend_meta.get("name", self.legend_key),
                source_accuracy=legend_meta.get("reported_accuracy", "N/A"),
            )
            self.finished.emit(result)

        except Exception as exc:
            self.finished.emit(exc)


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        i18n_init("en")
        self._last_result: AnalysisResult | None = None
        self._last_params: dict = {}
        self._last_temporal: dict | None = None
        self._last_temporal_years: tuple[int, int] = (0, 0)
        self._last_temporal_series: list[dict] | None = None
        self._last_compare: list[dict] | None = None
        self._setup_ui()
        self._setup_menu()
        self.setMinimumSize(1200, 750)
        self.setWindowTitle(t("app.title"))
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage(t("status.ready"))

    # ── UI setup ──────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # ── Left panel (input) ────────────────────────────────────────────
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)

        # Coordinate inputs
        self._lat_input = LatitudeInput(-23.55)
        self._lon_input = LongitudeInput(-46.63)
        self._radius_input = RadiusInput(5000)

        lay, self._lbl_lat, self._tip_lat = labeled_input_with_help(
            t("input.latitude"), self._lat_input, t("tips.latitude")
        )
        left_layout.addLayout(lay)
        lay, self._lbl_lon, self._tip_lon = labeled_input_with_help(
            t("input.longitude"), self._lon_input, t("tips.longitude")
        )
        left_layout.addLayout(lay)
        lay, self._lbl_rad, self._tip_rad = labeled_input_with_help(
            t("input.radius"), self._radius_input, t("tips.radius")
        )
        left_layout.addLayout(lay)

        # Paste "lat, lon" pair into either field fills both
        def _set_pair(lat: float, lon: float) -> None:
            self._lat_input.setValue(lat)
            self._lon_input.setValue(lon)
        self._lat_input.pair_pasted.connect(_set_pair)
        self._lon_input.pair_pasted.connect(_set_pair)

        # Source selector
        self._source_selector = SourceSelector()
        left_layout.addWidget(self._source_selector)

        # Analyze button
        self._btn_analyze = QPushButton(t("input.analyze"))
        self._btn_analyze.setStyleSheet(
            "QPushButton { background: #27ae60; color: white; padding: 10px; "
            "border-radius: 5px; font-size: 15px; font-weight: bold; }"
            "QPushButton:hover { background: #219a52; }"
            "QPushButton:disabled { background: #95a5a6; }"
        )
        self._btn_analyze.clicked.connect(self._run_analysis)
        left_layout.addWidget(self._btn_analyze)

        left_layout.addStretch()
        left.setMaximumWidth(400)
        splitter.addWidget(left)

        # ── Right panel (tabs: results / temporal / compare) ──────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        self._tabs = QTabWidget()

        # -- Tab 1: Single Analysis --
        tab_single = QWidget()
        tab_single_layout = QVBoxLayout(tab_single)

        # Map + results split vertically
        inner_splitter = QSplitter(Qt.Orientation.Vertical)

        self._map_viewer = MapViewer()
        inner_splitter.addWidget(self._map_viewer)

        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(0, 0, 0, 0)

        self._warnings_panel = WarningsPanel()
        results_layout.addWidget(self._warnings_panel)

        self._results_table = ResultsTable()
        results_layout.addWidget(self._results_table)

        self._metrics_panel = MetricsPanel()
        results_layout.addWidget(self._metrics_panel)
        results_layout.addStretch()

        results_scroll = QScrollArea()
        results_scroll.setWidgetResizable(True)
        results_scroll.setWidget(results_widget)
        inner_splitter.addWidget(results_scroll)
        inner_splitter.setSizes([350, 450])
        inner_splitter.setHandleWidth(6)
        inner_splitter.setChildrenCollapsible(False)

        tab_single_layout.addWidget(inner_splitter)
        self._tabs.addTab(tab_single, t("tabs.single"))

        # -- Tab 2: Temporal Analysis --
        self._temporal_panel = TemporalPanel()
        self._temporal_panel.analyze_requested.connect(self._run_temporal_analysis)
        self._temporal_panel.analyze_multi_requested.connect(self._run_temporal_series)
        self._tabs.addTab(self._temporal_panel, t("tabs.temporal"))

        # -- Tab 3: Compare Points --
        self._compare_panel = ComparePanel()
        self._compare_panel.compare_requested.connect(self._run_comparison)
        self._compare_panel.open_map_requested.connect(self._on_compare_open_map)
        self._compare_panel.bulk_download_requested.connect(self._on_compare_bulk_download)
        self._compare_panel.map_tiff_requested.connect(self._on_compare_map_tiff)
        self._tabs.addTab(self._compare_panel, t("tabs.compare"))

        # -- Tab 4: Compare Map --
        self._compare_map_viewer = MapViewer()
        self._tabs.addTab(self._compare_map_viewer, t("tabs.compare_map"))

        right_layout.addWidget(self._tabs)
        splitter.addWidget(right)
        splitter.setSizes([350, 850])
        splitter.setHandleWidth(6)
        splitter.setChildrenCollapsible(False)

    def _setup_menu(self) -> None:
        menu_bar = self.menuBar()
        menu_bar.clear()

        # File menu
        file_menu = menu_bar.addMenu(t("menu.file"))
        export_csv = QAction(t("menu.export_csv"), self)
        export_csv.triggered.connect(self._export_csv)
        file_menu.addAction(export_csv)

        export_xlsx = QAction(t("menu.export_xlsx"), self)
        export_xlsx.triggered.connect(self._export_xlsx)
        file_menu.addAction(export_xlsx)

        export_json = QAction(t("menu.export_json"), self)
        export_json.triggered.connect(self._export_json)
        file_menu.addAction(export_json)

        export_pdf = QAction(t("menu.export_pdf"), self)
        export_pdf.triggered.connect(self._export_pdf)
        file_menu.addAction(export_pdf)

        export_tiff = QAction(t("menu.export_compare_tiff"), self)
        export_tiff.triggered.connect(self._export_compare_tiff)
        file_menu.addAction(export_tiff)

        file_menu.addSeparator()
        exit_act = QAction(t("menu.exit"), self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # Settings menu
        settings_menu = menu_bar.addMenu(t("menu.settings"))
        settings_act = QAction(t("menu.settings"), self)
        settings_act.triggered.connect(self._open_settings)
        settings_menu.addAction(settings_act)

        # Help menu
        help_menu = menu_bar.addMenu(t("menu.help"))
        about_act = QAction(t("menu.about"), self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    # ── Analysis logic ────────────────────────────────────────────────────

    def _run_analysis(self) -> None:
        lat = self._lat_input.value()
        lon = self._lon_input.value()
        radius = self._radius_input.value()
        legend_key = self._source_selector.get_legend_key()

        if self._source_selector.is_remote:
            src = self._source_selector.selected_source
            if not src:
                QMessageBox.warning(self, "Error", "No remote source selected.")
                return
            try:
                source_path = resolve_remote_url(src["key"], lat, lon)
            except Exception as exc:
                QMessageBox.warning(self, "Error", f"Failed to resolve remote URL:\n{exc}")
                return
        else:
            source_path = self._source_selector.selected_file
            if not source_path:
                QMessageBox.warning(
                    self, "Error",
                    "Please select a local raster file."
                )
                return

        self._last_params = {
            "lat": lat, "lon": lon, "radius_m": radius,
            "legend_key": legend_key, "source_path": source_path,
        }

        # Show buffer on map
        gj = buffer_geojson(lon, lat, radius)
        self._map_viewer.show_buffer(lat, lon, radius, gj)

        # Run analysis in thread
        self._btn_analyze.setEnabled(False)
        self._status_bar.showMessage(t("status.analyzing"))

        self._thread = QThread()
        self._worker = AnalysisWorker(source_path, lon, lat, radius, legend_key)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_analysis_done(self, result: AnalysisResult | Exception) -> None:
        self._btn_analyze.setEnabled(True)

        if isinstance(result, Exception):
            self._status_bar.showMessage(t("status.error", msg=str(result)))
            QMessageBox.critical(
                self, "Analysis Error",
                f"An error occurred:\n\n{result}\n\n{traceback.format_exc()}"
            )
            return

        self._last_result = result
        self._results_table.update_results(result)
        self._metrics_panel.update_metrics(result.landscape_metrics, result.pixel_area_m2)
        self._warnings_panel.update_warnings(
            result.quality_warnings, result.total_valid_pixels
        )

        # Update map with results
        lat = self._last_params["lat"]
        lon = self._last_params["lon"]
        radius = self._last_params["radius_m"]
        gj = buffer_geojson(lon, lat, radius)
        self._map_viewer.show_results(lat, lon, radius, result.class_stats, gj)

        self._status_bar.showMessage(
            f"{t('status.done')} — {t('status.pixels_analyzed', n=result.total_valid_pixels)}"
        )

    # ── Temporal analysis ─────────────────────────────────────────────────

    def _run_temporal_analysis(
        self, file1: str, file2: str, year1: int, year2: int
    ) -> None:
        lat = self._lat_input.value()
        lon = self._lon_input.value()
        radius = self._radius_input.value()
        legend_key = self._source_selector.get_legend_key()

        try:
            self._status_bar.showMessage(t("status.analyzing"))
            legend_classes = load_legend_classes(legend_key)

            r1 = clip_raster_to_buffer(file1, lon, lat, radius)
            r2 = clip_raster_to_buffer(file2, lon, lat, radius)

            # Ensure same shape
            min_h = min(r1.data.shape[0], r2.data.shape[0])
            min_w = min(r1.data.shape[1], r2.data.shape[1])
            d1 = r1.data[:min_h, :min_w]
            d2 = r2.data[:min_h, :min_w]
            m1 = r1.valid_mask[:min_h, :min_w]
            m2 = r2.valid_mask[:min_h, :min_w]
            cs1 = compute_class_statistics(d1, m1, r1.pixel_area_m2, legend_classes)
            cs2 = compute_class_statistics(d2, m2, r2.pixel_area_m2, legend_classes)

            transition = compute_transition_matrix(
                d1, d2, m1, m2, r1.pixel_area_m2, legend_classes
            )
            transition["metrics_t1"] = compute_landscape_metrics(
                cs1, d1, m1, r1.pixel_area_m2
            )
            transition["metrics_t2"] = compute_landscape_metrics(
                cs2, d2, m2, r2.pixel_area_m2
            )
            self._last_temporal = transition
            self._last_temporal_years = (year1, year2)
            self._temporal_panel.update_results(transition, year1, year2)
            self._status_bar.showMessage(t("status.done"))

        except Exception as exc:
            self._status_bar.showMessage(t("status.error", msg=str(exc)))
            QMessageBox.critical(self, "Error", str(exc))

    def _run_temporal_series(self, year_file_pairs: list) -> None:
        """Analyse N individual years and display a longitudinal coverage table."""
        legend_key = self._source_selector.get_legend_key()
        lat = self._lat_input.value()
        lon = self._lon_input.value()
        radius = self._radius_input.value()

        try:
            self._status_bar.showMessage(t("status.analyzing"))
            legend_classes = load_legend_classes(legend_key)
            series: list[dict] = []

            for year, file_path in sorted(year_file_pairs, key=lambda x: x[0]):
                r = clip_raster_to_buffer(file_path, lon, lat, radius)
                cs = compute_class_statistics(
                    r.data, r.valid_mask, r.pixel_area_m2, legend_classes
                )
                lm = compute_landscape_metrics(
                    cs, r.data, r.valid_mask, r.pixel_area_m2
                )
                series.append({
                    "year": year,
                    "class_stats": cs,
                    "landscape_metrics": lm,
                })

            self._last_temporal_series = series
            self._temporal_panel.set_buffer_centre(lat, lon, radius)
            self._temporal_panel.update_series_results(series)
            self._status_bar.showMessage(t("status.done"))

        except Exception as exc:
            self._status_bar.showMessage(t("status.error", msg=str(exc)))
            QMessageBox.critical(self, "Error", str(exc))

    # ── Multi-point comparison ────────────────────────────────────────────

    def _run_comparison(self, points: list) -> None:
        """points: list[ComparePoint] with .name .lat .lon .radius"""
        source_path = self._source_selector.selected_file
        legend_key = self._source_selector.get_legend_key()

        if not source_path:
            QMessageBox.warning(self, "Error", "Select a local file first.")
            return

        try:
            self._status_bar.showMessage(t("status.analyzing"))
            legend_classes = load_legend_classes(legend_key)
            results = []

            for i, p in enumerate(points):
                # Back-compat: accept raw tuples (lat, lon, radius) too
                if isinstance(p, tuple):
                    lat, lon, radius = p
                    label = f"P{i+1}"
                else:
                    lat, lon, radius = p.lat, p.lon, p.radius
                    label = p.name

                raster = clip_raster_to_buffer(source_path, lon, lat, radius)
                cs = compute_class_statistics(
                    raster.data, raster.valid_mask,
                    raster.pixel_area_m2, legend_classes
                )
                lm = compute_landscape_metrics(
                    cs, raster.data, raster.valid_mask, raster.pixel_area_m2
                )
                results.append({
                    "point_label": label,
                    "class_stats": cs,
                    "landscape_metrics": lm,
                })

            self._last_compare = results
            self._compare_panel.update_results(results)

            # Update compare map tab
            map_points = []
            for i, p in enumerate(points):
                if isinstance(p, tuple):
                    lat_p, lon_p, radius_p = p
                    lbl = f"P{i+1}"
                else:
                    lat_p, lon_p, radius_p = p.lat, p.lon, p.radius
                    lbl = p.name
                map_points.append({"label": lbl, "lat": lat_p, "lon": lon_p, "radius_m": radius_p})
            grad_vals = [r["landscape_metrics"].isa_index for r in results]
            self._compare_map_viewer.show_compare_points(
                map_points, gradient_values=grad_vals, gradient_label="ISA (%)",
            )

            self._status_bar.showMessage(t("status.done"))

        except Exception as exc:
            self._status_bar.showMessage(t("status.error", msg=str(exc)))
            QMessageBox.critical(self, "Error", str(exc))

    # ── Exports ───────────────────────────────────────────────────────────

    def _export_csv(self) -> None:
        if not self._last_result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "luma_results.csv", "CSV (*.csv)"
        )
        if not path:
            return
        result = self._last_result
        with open(path, "w", encoding="utf-8") as f:
            f.write("class_id,class_name,pixels,area_m2,area_km2,area_ha,percentage,num_patches,largest_patch_m2,color\n")
            for cs in result.class_stats:
                f.write(
                    f"{cs.class_id},{cs.class_name},{cs.pixel_count},"
                    f"{cs.area_m2:.2f},{cs.area_m2/1e6:.6f},{cs.area_m2/10000:.4f},"
                    f"{cs.percentage:.2f},{cs.num_patches},"
                    f"{cs.largest_patch_area_m2:.2f},{cs.color}\n"
                )
        self._status_bar.showMessage(f"CSV exported to {path}")

    def _export_xlsx(self) -> None:
        """Export all available analyses to a multi-sheet .xlsx file."""
        if not (
            self._last_result or self._last_temporal
            or self._last_temporal_series or self._last_compare
        ):
            QMessageBox.warning(self, "Error", "No analysis results to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Excel", "luma_results.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return

        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
        except ImportError:
            QMessageBox.critical(
                self, "Error",
                "openpyxl is required for Excel export. Install with: pip install openpyxl",
            )
            return

        wb = openpyxl.Workbook()
        # Remove default sheet (we'll create our own)
        wb.remove(wb.active)

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")

        def _write_header(ws, row_idx: int, headers: list[str]) -> None:
            for col, val in enumerate(headers, 1):
                cell = ws.cell(row=row_idx, column=col, value=val)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")

        # ── Sheet: Classes (single analysis) ────────────────────────────
        if self._last_result:
            ws = wb.create_sheet("Classes")
            _write_header(ws, 1, [
                "class_id", "class_name", "pixels", "area_m2",
                "area_km2", "area_ha", "percentage", "num_patches",
                "largest_patch_m2", "color",
            ])
            for i, cs in enumerate(self._last_result.class_stats, 2):
                ws.cell(row=i, column=1, value=cs.class_id)
                ws.cell(row=i, column=2, value=cs.class_name)
                ws.cell(row=i, column=3, value=cs.pixel_count)
                ws.cell(row=i, column=4, value=round(cs.area_m2, 2))
                ws.cell(row=i, column=5, value=round(cs.area_m2 / 1e6, 6))
                ws.cell(row=i, column=6, value=round(cs.area_m2 / 10_000, 4))
                ws.cell(row=i, column=7, value=round(cs.percentage, 2))
                ws.cell(row=i, column=8, value=cs.num_patches)
                ws.cell(row=i, column=9, value=round(cs.largest_patch_area_m2, 2))
                ws.cell(row=i, column=10, value=cs.color)

            # Metrics sheet
            ws_m = wb.create_sheet("Metrics")
            _write_header(ws_m, 1, ["metric", "value"])
            m = self._last_result.landscape_metrics
            rows = [
                ("shannon_diversity", m.shannon_diversity),
                ("isa_index", m.isa_index),
                ("simpson_diversity", m.simpson_diversity),
                ("dominance", m.dominance),
                ("evenness", m.evenness),
                ("total_patches", m.total_patches),
                ("patch_density", m.patch_density),
                ("largest_patch_index", m.largest_patch_index),
                ("edge_density", m.edge_density),
                ("effective_mesh_size", m.effective_mesh_size),
                ("aggregation_index", m.aggregation_index),
                ("contagion", m.contagion),
                ("mean_shape_index", m.mean_shape_index),
            ]
            for i, (k, v) in enumerate(rows, 2):
                ws_m.cell(row=i, column=1, value=k)
                ws_m.cell(row=i, column=2, value=v)

        # ── Sheet: Temporal ─────────────────────────────────────────────
        if self._last_temporal:
            ws = wb.create_sheet("Temporal")
            td = self._last_temporal
            classes = td["classes"]
            legend = td["legend"]
            matrix = td["matrix"]
            net_change = td["net_change"]
            y1, y2 = self._last_temporal_years
            class_names = [legend.get(c, {}).get("name", f"Class {c}") for c in classes]

            ws.cell(row=1, column=1, value=f"Transition matrix (km²) — {y1} → {y2}")
            ws.cell(row=1, column=1).font = Font(bold=True)
            _write_header(ws, 2, [f"from \\ to ({y1} → {y2})"] + class_names)
            for i, c1 in enumerate(classes):
                ws.cell(row=3 + i, column=1, value=class_names[i])
                ws.cell(row=3 + i, column=1).font = Font(bold=True)
                for j, c2 in enumerate(classes):
                    ws.cell(row=3 + i, column=2 + j, value=round(matrix[c1].get(c2, 0) / 1e6, 4))

            base = 3 + len(classes) + 2
            ws.cell(row=base, column=1, value="Persistence (%)").font = Font(bold=True)
            ws.cell(row=base, column=2, value=td["persistence"])
            ws.cell(row=base + 2, column=1, value="Net change by class (km²)").font = Font(bold=True)
            _write_header(ws, base + 3, ["class", "net_change_km2"])
            for i, c in enumerate(classes):
                ws.cell(row=base + 4 + i, column=1, value=class_names[i])
                ws.cell(row=base + 4 + i, column=2, value=round(net_change.get(c, 0) / 1e6, 4))
            if "metrics_t1" in td and "metrics_t2" in td:
                isa_base = base + 4 + len(classes) + 2
                ws.cell(row=isa_base, column=1, value=f"ISA {y1} (%)").font = Font(bold=True)
                ws.cell(row=isa_base, column=2, value=td["metrics_t1"].isa_index)
                ws.cell(row=isa_base + 1, column=1, value=f"ISA {y2} (%)").font = Font(bold=True)
                ws.cell(row=isa_base + 1, column=2, value=td["metrics_t2"].isa_index)
                ws.cell(row=isa_base + 2, column=1, value="ISA delta (p.p.)").font = Font(bold=True)
                ws.cell(
                    row=isa_base + 2,
                    column=2,
                    value=round(td["metrics_t2"].isa_index - td["metrics_t1"].isa_index, 2),
                )

        # ── Sheet: Compare points (points = rows, classes + metrics = cols)
        if self._last_temporal_series:
            ws = wb.create_sheet("Temporal Series")
            series = self._last_temporal_series
            years = [entry["year"] for entry in series]
            _write_header(ws, 1, ["metric"] + [str(y) for y in years])
            ws.cell(row=2, column=1, value="isa_index")
            for col, entry in enumerate(series, 2):
                ws.cell(row=2, column=col, value=entry["landscape_metrics"].isa_index)

            all_classes: list[str] = []
            seen = set()
            for entry in series:
                for cs in entry["class_stats"]:
                    if cs.class_name not in seen:
                        all_classes.append(cs.class_name)
                        seen.add(cs.class_name)
            for row, cls_name in enumerate(all_classes, 3):
                ws.cell(row=row, column=1, value=f"%_{cls_name}")
                for col, entry in enumerate(series, 2):
                    pct = next(
                        (cs.percentage for cs in entry["class_stats"] if cs.class_name == cls_name),
                        0.0,
                    )
                    ws.cell(row=row, column=col, value=round(pct, 2))

        if self._last_compare:
            ws = wb.create_sheet("Compare")
            all_classes: list[str] = []
            seen = set()
            for r in self._last_compare:
                for cs in r["class_stats"]:
                    if cs.class_name not in seen:
                        all_classes.append(cs.class_name)
                        seen.add(cs.class_name)

            metric_cols = [
                ("shannon_diversity", lambda m: m.shannon_diversity),
                ("isa_index", lambda m: m.isa_index),
                ("simpson_diversity", lambda m: m.simpson_diversity),
                ("evenness", lambda m: m.evenness),
                ("total_patches", lambda m: m.total_patches),
                ("patch_density", lambda m: m.patch_density),
                ("largest_patch_index", lambda m: m.largest_patch_index),
                ("largest_patch_area_m2", lambda m: m.largest_patch_area_m2),
                ("smallest_patch_area_m2", lambda m: m.smallest_patch_area_m2),
                ("mean_patch_area_m2", lambda m: m.mean_patch_area_m2),
                ("aggregation_index", lambda m: m.aggregation_index),
                ("contagion", lambda m: m.contagion),
                ("mean_shape_index", lambda m: m.mean_shape_index),
            ]

            headers = ["point"] + [f"%_{c}" for c in all_classes] + [n for n, _ in metric_cols]
            _write_header(ws, 1, headers)

            for i, r in enumerate(self._last_compare, 2):
                ws.cell(row=i, column=1, value=r["point_label"])
                for c_off, cls_name in enumerate(all_classes):
                    pct = 0.0
                    for cs in r["class_stats"]:
                        if cs.class_name == cls_name:
                            pct = cs.percentage
                            break
                    ws.cell(row=i, column=2 + c_off, value=round(pct, 2))
                lm = r["landscape_metrics"]
                for m_off, (_, acc) in enumerate(metric_cols):
                    col = 2 + len(all_classes) + m_off
                    ws.cell(row=i, column=col, value=acc(lm))

        try:
            wb.save(path)
        except PermissionError:
            QMessageBox.critical(self, "Error",
                "File is open in another program. Close it and try again.")
            return

        self._status_bar.showMessage(f"Excel exported to {path}")

    def _export_json(self) -> None:
        if not self._last_result:
            return
        import json
        path, _ = QFileDialog.getSaveFileName(
            self, "Export JSON", "luma_results.json", "JSON (*.json)"
        )
        if not path:
            return
        result = self._last_result
        data = {
            "parameters": self._last_params,
            "total_area_m2": result.total_area_m2,
            "total_pixels": result.total_valid_pixels,
            "source": result.source_name,
            "accuracy": result.source_accuracy,
            "classes": [
                {
                    "id": cs.class_id,
                    "name": cs.class_name,
                    "pixels": cs.pixel_count,
                    "area_m2": cs.area_m2,
                    "percentage": cs.percentage,
                    "num_patches": cs.num_patches,
                    "largest_patch_m2": cs.largest_patch_area_m2,
                }
                for cs in result.class_stats
            ],
            "landscape_metrics": {
                "shannon_diversity": result.landscape_metrics.shannon_diversity,
                "isa_index": result.landscape_metrics.isa_index,
                "simpson_diversity": result.landscape_metrics.simpson_diversity,
                "dominance": result.landscape_metrics.dominance,
                "evenness": result.landscape_metrics.evenness,
                "total_patches": result.landscape_metrics.total_patches,
                "patch_density": result.landscape_metrics.patch_density,
                "largest_patch_index": result.landscape_metrics.largest_patch_index,
                "edge_density": result.landscape_metrics.edge_density,
                "effective_mesh_size": result.landscape_metrics.effective_mesh_size,
                "aggregation_index": result.landscape_metrics.aggregation_index,
                "contagion": result.landscape_metrics.contagion,
                "mean_shape_index": result.landscape_metrics.mean_shape_index,
            },
            "warnings": result.quality_warnings,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self._status_bar.showMessage(f"JSON exported to {path}")

    def _export_pdf(self) -> None:
        has_any = (
            self._last_result or self._last_temporal
            or self._last_temporal_series or self._last_compare
        )
        if not has_any:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", "luma_report.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            from luma.output.report import generate_pdf_report
            # Capture compare map if available
            compare_map_img: bytes | None = None
            if self._last_compare:
                pix = self._compare_map_viewer.grab_map()
                if pix and not pix.isNull():
                    import io
                    from PySide6.QtCore import QBuffer, QIODevice
                    buf = QBuffer()
                    buf.open(QIODevice.OpenModeFlag.WriteOnly)
                    pix.save(buf, "PNG")
                    compare_map_img = bytes(buf.data())

            generate_pdf_report(
                path=path,
                result=self._last_result,
                params=self._last_params,
                lang=get_language(),
                temporal_data=self._last_temporal,
                temporal_years=self._last_temporal_years,
                compare_data=self._last_compare,
                temporal_series=self._last_temporal_series,
                compare_map_img=compare_map_img,
            )
            self._status_bar.showMessage(f"PDF exported to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"PDF export failed:\n{exc}")

    def _on_compare_open_map(self, points: list) -> None:
        map_points = []
        for i, p in enumerate(points):
            map_points.append({"label": p.name, "lat": p.lat, "lon": p.lon, "radius_m": p.radius})
        self._compare_map_viewer.show_compare_points(map_points)
        self._tabs.setCurrentIndex(3)

    def _on_compare_bulk_download(self, target_dir: str) -> None:
        """Export points + buffers + map to .kmz/.kml/.shp/.tiff bundle."""
        if not self._last_compare:
            QMessageBox.warning(self, "", t("compare_extra.bulk_download_no_data"))
            return
        try:
            from pathlib import Path as _P
            import zipfile
            from luma.core.buffer import buffer_geojson
            base = _P(target_dir)
            base.mkdir(parents=True, exist_ok=True)

            # Recover the original ComparePoint geometry from compare results.
            # _last_compare only has labels + stats; pull lat/lon from compare panel state.
            # The compare panel rebuilds points via _collect_points; ask it instead.
            try:
                pts = self._compare_panel._collect_points()
            except Exception:
                pts = []

            # KML + KMZ via simplekml
            import simplekml
            kml = simplekml.Kml()
            for p in pts:
                pnt = kml.newpoint(name=p.name, coords=[(p.lon, p.lat)])
                pnt.style.iconstyle.color = simplekml.Color.red
                gj = buffer_geojson(p.lon, p.lat, p.radius)
                coords = gj["coordinates"][0]
                pol = kml.newpolygon(
                    name=f"{p.name} buffer",
                    outerboundaryis=[(x, y) for x, y in coords],
                )
                pol.style.linestyle.color = simplekml.Color.red
                pol.style.polystyle.color = simplekml.Color.changealphaint(60, simplekml.Color.red)
            kml_path = base / "points_buffers.kml"
            kmz_path = base / "points_buffers.kmz"
            kml.save(str(kml_path))
            kml.savekmz(str(kmz_path))

            # Shapefile via pyshp — write points + buffer polygons (two shapefiles)
            import shapefile as _shp
            pts_w = _shp.Writer(str(base / "points"), shapeType=_shp.POINT)
            pts_w.field("name", "C", size=64)
            pts_w.field("lat", "F", decimal=6)
            pts_w.field("lon", "F", decimal=6)
            pts_w.field("radius_m", "F", decimal=2)
            for p in pts:
                pts_w.point(p.lon, p.lat)
                pts_w.record(p.name, p.lat, p.lon, p.radius)
            pts_w.close()
            with open(base / "points.prj", "w") as f:
                f.write(
                    'GEOGCS["WGS 84",DATUM["WGS_1984",'
                    'SPHEROID["WGS 84",6378137,298.257223563]],'
                    'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]'
                )

            buf_w = _shp.Writer(str(base / "buffers"), shapeType=_shp.POLYGON)
            buf_w.field("name", "C", size=64)
            buf_w.field("radius_m", "F", decimal=2)
            for p in pts:
                gj = buffer_geojson(p.lon, p.lat, p.radius)
                ring = [(x, y) for x, y in gj["coordinates"][0]]
                buf_w.poly([ring])
                buf_w.record(p.name, p.radius)
            buf_w.close()
            with open(base / "buffers.prj", "w") as f:
                f.write(
                    'GEOGCS["WGS 84",DATUM["WGS_1984",'
                    'SPHEROID["WGS 84",6378137,298.257223563]],'
                    'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]'
                )

            # Map TIFF with legend
            tiff_path = base / "compare_map.tif"
            class_stats = self._last_compare[0]["class_stats"] if self._last_compare else None
            self._compare_map_viewer.export_tiff_with_legend(
                str(tiff_path), class_stats=class_stats, title=t("tabs.compare_map"),
            )

            self._status_bar.showMessage(t("compare_extra.bulk_download_done", path=str(base)))
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Bulk export failed:\n{exc}\n{traceback.format_exc()}")

    def _on_compare_map_tiff(self, path: str) -> None:
        class_stats = self._last_compare[0]["class_stats"] if self._last_compare else None
        ok = self._compare_map_viewer.export_tiff_with_legend(
            path, class_stats=class_stats, title=t("tabs.compare_map"),
        )
        if ok:
            self._status_bar.showMessage(f"TIFF exported to {path}")
        else:
            QMessageBox.warning(self, "Error", t("menu.compare_tiff_no_map"))

    def _export_compare_tiff(self) -> None:
        """Save the compare map as a high-quality TIFF for publication."""
        if not self._last_compare:
            QMessageBox.information(self, "", t("menu.compare_tiff_no_data"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, t("menu.export_compare_tiff"), "luma_compare_map.tif",
            "TIFF (*.tif *.tiff)",
        )
        if not path:
            return
        pix = self._compare_map_viewer.grab_map()
        if pix is None or pix.isNull():
            QMessageBox.warning(self, "Error", t("menu.compare_tiff_no_map"))
            return
        if pix.save(path, "TIFF"):
            self._status_bar.showMessage(f"TIFF exported to {path}")
        else:
            QMessageBox.critical(self, "Error", f"Failed to save TIFF: {path}")

    # ── Dialogs ───────────────────────────────────────────────────────────

    def _show_about(self) -> None:
        dlg = AboutDialog(self)
        dlg.exec()

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self)
        dlg.language_changed.connect(self._on_language_changed)
        dlg.exec()

    def _on_language_changed(self, lang: str) -> None:
        set_language(lang)
        self.setWindowTitle(t("app.title"))
        self._btn_analyze.setText(t("input.analyze"))

        # Update input labels and help bubbles
        self._lbl_lat.setText(t("input.latitude"))
        self._lbl_lon.setText(t("input.longitude"))
        self._lbl_rad.setText(t("input.radius"))
        self._tip_lat.set_tip(t("tips.latitude"))
        self._tip_lon.set_tip(t("tips.longitude"))
        self._tip_rad.set_tip(t("tips.radius"))

        self._source_selector.refresh_texts()
        self._results_table.refresh_texts()
        self._metrics_panel.refresh_texts()
        self._temporal_panel.refresh_texts()
        self._compare_panel.refresh_texts()
        self._tabs.setTabText(0, t("tabs.single"))
        self._tabs.setTabText(1, t("tabs.temporal"))
        self._tabs.setTabText(2, t("tabs.compare"))
        self._tabs.setTabText(3, t("tabs.compare_map"))
        self._status_bar.showMessage(t("status.ready"))
        self._setup_menu()
