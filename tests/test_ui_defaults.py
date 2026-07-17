import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from luma.gui.main_window import MainWindow
from luma.gui.widgets.results_table import ResultsTable
from luma.gui.widgets.help_bubble import HelpBubble
from luma.gui.widgets.compare_panel import PointRow
from luma.gui.widgets.aoi_widget import AOIWidget
from luma.i18n.translator import set_language


def test_main_window_starts_in_brazilian_portuguese():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        assert "Analisador" in window.windowTitle()
        assert window._btn_analyze.text() == "Analisar"
        assert window._objective_selector.selected_objective == "single"
        assert window.minimumWidth() <= 1024
        assert window._result_tabs.count() == 2
        window.resize(900, 640)
        window.show()
        app.processEvents()
        assert window._main_splitter.sizes()[0] >= 240
        assert window._btn_analyze.parentWidget() is window._left_column
        window._objective_selector._combo.setCurrentIndex(1)
        assert window._tabs.currentIndex() == 1
        assert window._temporal_scroll.horizontalScrollBar().maximum() == 0
        window._tabs.setCurrentIndex(4)
        assert window._objective_selector.selected_objective == "compare_aois"
        window.resize(700, 520)
        app.processEvents()
        assert window._left_column.isHidden()
        assert window._right_panel.isVisible()
        assert window._compact_controls.isVisible()
        window._btn_open_inputs.click()
        app.processEvents()
        assert window._left_column.isVisible()
        assert window._right_panel.isHidden()
        assert window._btn_compact_results.isVisible()
        assert window._left_column.width() >= 600
        window._btn_compact_results.click()
        app.processEvents()
        assert window._left_column.isHidden()
        assert window._right_panel.isVisible()
        window.resize(900, 640)
        app.processEvents()
        assert not window._left_column.isHidden()
        assert window._right_panel.isVisible()
        assert window._compact_controls.isHidden()
    finally:
        window.close()
        app.processEvents()


def test_results_table_explains_its_empty_state():
    app = QApplication.instance() or QApplication([])
    table = ResultsTable()
    try:
        assert "aparecerão aqui" in table._info_label.text()
        table.clear()
        assert "aparecerão aqui" in table._info_label.text()
    finally:
        table.close()
        app.processEvents()


def test_icon_buttons_have_accessible_touch_targets():
    app = QApplication.instance() or QApplication([])
    bubble = HelpBubble("Ajuda sobre o campo")
    point = PointRow(0)
    try:
        assert bubble.minimumWidth() >= 32
        assert bubble.minimumHeight() >= 32
        assert point.btn_remove.minimumWidth() >= 32
        assert point.btn_remove.accessibleName()
    finally:
        bubble.close()
        point.close()
        app.processEvents()


def test_aoi_controls_refresh_completely_in_english():
    app = QApplication.instance() or QApplication([])
    widget = AOIWidget()
    try:
        set_language("en")
        widget.refresh_texts()
        assert widget.btn_draw.text() == "Draw polygon"
        assert widget._status.text() == "No area selected"
        widget.start_drawing()
        assert widget._status.text().startswith("Click the map")
    finally:
        set_language("pt_BR")
        widget.close()
        app.processEvents()
