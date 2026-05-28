"""Settings dialog — language selection and cache management."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGroupBox, QMessageBox,
)
from PySide6.QtCore import Signal

from luma.i18n.translator import t, AVAILABLE_LANGUAGES, get_language, set_language
from luma.core.downloader import get_cache_size_mb, clear_cache


class SettingsDialog(QDialog):

    language_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("menu.settings"))
        self.setMinimumWidth(380)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Language
        lang_group = QGroupBox(t("menu.language"))
        lang_layout = QHBoxLayout(lang_group)
        self._combo_lang = QComboBox()
        current = get_language()
        for code, name in AVAILABLE_LANGUAGES.items():
            self._combo_lang.addItem(name, userData=code)
            if code == current:
                self._combo_lang.setCurrentIndex(self._combo_lang.count() - 1)
        self._combo_lang.currentIndexChanged.connect(self._on_lang_changed)
        lang_layout.addWidget(self._combo_lang)
        layout.addWidget(lang_group)

        # Cache
        cache_group = QGroupBox("Cache")
        cache_layout = QVBoxLayout(cache_group)
        self._cache_label = QLabel(
            t("status.cache_size", size=get_cache_size_mb())
        )
        cache_layout.addWidget(self._cache_label)
        btn_clear = QPushButton(t("menu.clear_cache"))
        btn_clear.clicked.connect(self._clear_cache)
        cache_layout.addWidget(btn_clear)
        layout.addWidget(cache_group)

        # Close
        row = QHBoxLayout()
        row.addStretch()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        row.addWidget(btn_ok)
        layout.addLayout(row)

    def _on_lang_changed(self) -> None:
        lang = self._combo_lang.currentData()
        if lang and lang != get_language():
            set_language(lang)
            self.language_changed.emit(lang)

    def _clear_cache(self) -> None:
        n = clear_cache()
        self._cache_label.setText(
            t("status.cache_size", size=get_cache_size_mb())
        )
        QMessageBox.information(
            self,
            "Cache",
            t("status.cache_cleared", n=n),
        )
