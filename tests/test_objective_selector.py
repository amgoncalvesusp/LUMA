import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from luma.gui.widgets.objective_selector import ObjectiveSelector


def test_objective_selector_exposes_three_guided_paths():
    app = QApplication.instance() or QApplication([])
    selector = ObjectiveSelector()
    assert selector.objectives == ["single", "temporal", "compare", "compare_aois"]
    assert selector._combo.count() == 4
    selector._combo.setCurrentIndex(1)
    assert selector.selected_objective == "temporal"
    selector.close()
    app.processEvents()
