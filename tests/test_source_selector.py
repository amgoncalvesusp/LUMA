import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from luma.gui.widgets.source_selector import SourceSelector


def test_remote_source_exposes_declared_year():
    app = QApplication.instance() or QApplication([])
    widget = SourceSelector()
    try:
        index = widget._combo_source.findText("Collection 10.1", Qt.MatchFlag.MatchContains)
        assert index >= 0
        widget._combo_source.setCurrentIndex(index)
        widget._radio_remote.setChecked(True)
        assert widget.selected_year == 2024
        assert widget.get_legend_key() == "mapbiomas_col10"
    finally:
        widget.close()
        app.processEvents()


def test_source_selector_restores_remote_project_selection():
    app = QApplication.instance() or QApplication([])
    widget = SourceSelector()
    try:
        widget.apply_project(
            source_key="mapbiomas_brazil_col3_10m",
            source_year=2020,
            legend_key="mapbiomas_col10",
            source_file=None,
        )
        assert widget.is_remote
        assert widget.selected_source_key == "mapbiomas_brazil_col3_10m"
        assert widget.selected_year == 2020
    finally:
        widget.close()
        app.processEvents()
