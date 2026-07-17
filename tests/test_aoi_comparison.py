import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from shapely.geometry import Polygon

from luma.core.aoi import AOI
from luma.gui.widgets.aoi_comparison_panel import AOIComparisonPanel
from luma.gui.widgets.results_table import ResultsTable
from types import SimpleNamespace


def test_aoi_comparison_panel_keeps_named_areas():
    app = QApplication.instance() or QApplication([])
    panel = AOIComparisonPanel()
    panel.add_aoi(AOI(Polygon([(0, 0), (0, 1), (1, 0), (0, 0)])), "Área 1")
    panel.add_aoi(AOI(Polygon([(2, 2), (2, 3), (3, 2), (2, 2)])), "Área 2")

    assert [label for label, _ in panel.areas] == ["Área 1", "Área 2"]
    panel.close()
    app.processEvents()


def test_aoi_comparison_results_render_without_analysis_result_wrapper():
    app = QApplication.instance() or QApplication([])
    table = ResultsTable()
    table.update_aoi_comparison([{
        "point_label": "Área 1",
        "class_stats": [SimpleNamespace(class_name="Floresta", percentage=75.0)],
        "landscape_metrics": SimpleNamespace(total_patches=3),
        "geometry_area_m2": 1_000_000.0,
    }])
    assert table._table.rowCount() == 1
    assert table._table.item(0, 1).text() == "Floresta"
    table.close()
    app.processEvents()
