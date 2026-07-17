import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from luma.core.stats import AnalysisResult, ClassStats, LandscapeMetrics
from luma.gui.widgets.results_table import SummaryPanel
from luma.i18n.translator import set_language


def test_summary_panel_explains_dominant_and_impervious_classes():
    app = QApplication.instance() or QApplication([])
    set_language("pt_BR")
    panel = SummaryPanel()
    result = AnalysisResult(
        class_stats=[
            ClassStats(1, "Floresta", 60, 6000, 60.0, color="#0a0"),
            ClassStats(2, "Área urbana", 40, 4000, 40.0, color="#f00", impervious=True),
        ],
        landscape_metrics=LandscapeMetrics(isa_index=40.0),
        total_area_m2=10000,
        total_valid_pixels=100,
        source_name="MapBiomas",
    )
    panel.update_result(result)
    try:
        text = panel._label.text()
        assert "Floresta" in text
        assert "60,0%" in text or "60.0%" in text
        assert "40,0%" in text or "40.0%" in text
    finally:
        panel.close()
        app.processEvents()
