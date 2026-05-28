"""Data source selection widget — local file or remote dataset with download links."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QRadioButton, QComboBox,
    QPushButton, QFileDialog, QLabel, QButtonGroup, QGroupBox,
)
from PySide6.QtCore import Signal, Qt, QUrl
from PySide6.QtGui import QDesktopServices

from luma.i18n.translator import t
from luma.sources.catalog import list_sources, list_legends
from luma.gui.widgets.legend_preview import LegendPreviewDialog


class SourceSelector(QGroupBox):
    """Widget for selecting a data source (remote dataset or local file)."""

    source_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(t("input.source"), parent)
        self._selected_file: str = ""
        self._sources_list: list[dict] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Radio buttons
        self._btn_group = QButtonGroup(self)
        self._radio_remote = QRadioButton(t("input.remote_dataset"))
        self._radio_local = QRadioButton(t("input.local_file"))
        self._radio_local.setChecked(True)
        self._btn_group.addButton(self._radio_remote, 0)
        self._btn_group.addButton(self._radio_local, 1)

        layout.addWidget(self._radio_remote)

        # Remote dataset combo
        remote_row = QHBoxLayout()
        self._combo_source = QComboBox()
        self._populate_sources()
        remote_row.addWidget(self._combo_source, stretch=1)
        layout.addLayout(remote_row)

        layout.addWidget(self._radio_local)

        # Local file picker
        file_row = QHBoxLayout()
        self._btn_file = QPushButton(t("input.select_file"))
        self._lbl_file = QLabel("")
        self._lbl_file.setStyleSheet("color: #666; font-size: 11px;")
        file_row.addWidget(self._btn_file)
        file_row.addWidget(self._lbl_file, stretch=1)
        layout.addLayout(file_row)

        # Legend selector (+ preview button)
        legend_row = QHBoxLayout()
        legend_row.addWidget(QLabel(t("input.legend")))
        self._combo_legend = QComboBox()
        self._populate_legends()
        legend_row.addWidget(self._combo_legend, stretch=1)

        self._btn_legend_preview = QPushButton("👁")
        self._btn_legend_preview.setToolTip(t("input.legend_preview"))
        self._btn_legend_preview.setFixedSize(32, 28)
        self._btn_legend_preview.clicked.connect(self._open_legend_preview)
        legend_row.addWidget(self._btn_legend_preview)
        layout.addLayout(legend_row)

        # ── Download links panel ──────────────────────────────────────────
        self._download_box = QGroupBox(t("input.download_data"))
        dl_layout = QVBoxLayout(self._download_box)
        dl_layout.setSpacing(4)

        self._combo_download = QComboBox()
        self._populate_download_sources()
        dl_layout.addWidget(self._combo_download)

        self._lbl_instructions = QLabel("")
        self._lbl_instructions.setWordWrap(True)
        self._lbl_instructions.setStyleSheet(
            "color: #555; font-size: 11px; padding: 4px 0;"
        )
        dl_layout.addWidget(self._lbl_instructions)

        self._btn_open_link = QPushButton(t("input.open_download_page"))
        self._btn_open_link.setStyleSheet(
            "QPushButton { background: #2980b9; color: white; padding: 5px 12px; "
            "border-radius: 3px; font-size: 12px; }"
            "QPushButton:hover { background: #2471a3; }"
        )
        self._btn_open_link.clicked.connect(self._open_download_link)
        dl_layout.addWidget(self._btn_open_link)

        layout.addWidget(self._download_box)

        # Connections
        self._btn_file.clicked.connect(self._pick_file)
        self._radio_remote.toggled.connect(self._on_mode_changed)
        self._radio_local.toggled.connect(self._on_mode_changed)
        self._combo_source.currentIndexChanged.connect(
            lambda: self.source_changed.emit()
        )
        self._combo_legend.currentIndexChanged.connect(
            lambda: self.source_changed.emit()
        )
        self._combo_download.currentIndexChanged.connect(
            self._on_download_source_changed
        )

        self._on_mode_changed()
        self._on_download_source_changed()

    def _populate_sources(self) -> None:
        self._combo_source.clear()
        self._sources_list = [s for s in list_sources() if s.get("type") == "remote_cog"]
        for src in self._sources_list:
            label = f"{src['name']}  [{src['resolution']}]"
            self._combo_source.addItem(label, userData=src)

    def _populate_legends(self) -> None:
        self._combo_legend.clear()
        self._combo_legend.addItem(t("input.auto_detect"), userData=None)
        for leg in list_legends():
            label = f"{leg['name']}  ({leg['num_classes']} classes)"
            self._combo_legend.addItem(label, userData=leg)

    def _populate_download_sources(self) -> None:
        self._combo_download.clear()
        sources = list_sources()
        for src in sources:
            if src.get("download_url"):
                label = f"{src['name']}  [{src['resolution']}]"
                self._combo_download.addItem(label, userData=src)

    def _on_download_source_changed(self) -> None:
        src = self._combo_download.currentData()
        if src and src.get("download_instructions"):
            self._lbl_instructions.setText(src["download_instructions"])
        else:
            self._lbl_instructions.setText("")

    def _open_legend_preview(self) -> None:
        key = self.get_legend_key()
        dlg = LegendPreviewDialog(key, self)
        dlg.exec()

    def _open_download_link(self) -> None:
        src = self._combo_download.currentData()
        if src and src.get("download_url"):
            QDesktopServices.openUrl(QUrl(src["download_url"]))

    def _pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("input.select_file"),
            "",
            "GeoTIFF (*.tif *.tiff);;All Files (*)",
        )
        if path:
            self._selected_file = path
            name = Path(path).name
            self._lbl_file.setText(name)
            self._radio_local.setChecked(True)
            self.source_changed.emit()

    def _on_mode_changed(self) -> None:
        is_remote = self._radio_remote.isChecked()
        self._combo_source.setEnabled(is_remote)
        self._btn_file.setEnabled(not is_remote)
        self._combo_legend.setEnabled(not is_remote)

    @property
    def is_remote(self) -> bool:
        return self._radio_remote.isChecked()

    @property
    def selected_source(self) -> dict | None:
        if self.is_remote:
            return self._combo_source.currentData()
        return None

    @property
    def selected_file(self) -> str:
        return self._selected_file

    @property
    def selected_legend_key(self) -> str | None:
        data = self._combo_legend.currentData()
        if data is None:
            return None
        return data.get("key")

    def get_legend_key(self) -> str:
        """Return the effective legend key for the current selection."""
        if self.is_remote:
            src = self.selected_source
            if src:
                return src.get("legend", "esa_worldcover")
        manual = self.selected_legend_key
        if manual:
            return manual
        # Auto-detect from filename
        if self._selected_file:
            fname = Path(self._selected_file).stem.lower()
            if "mapbiomas" in fname:
                if "col9" in fname or "coll9" in fname or "collection9" in fname or "collection_9" in fname:
                    return "mapbiomas_col9"
                return "mapbiomas_col10"
            if "worldcover" in fname or "esa" in fname:
                return "esa_worldcover"
            if "copernicus" in fname:
                return "copernicus_glc"
            if "modis" in fname or "mcd12" in fname:
                return "modis_igbp"
            if "dynamic" in fname:
                return "dynamic_world"
        return "esa_worldcover"

    def refresh_texts(self) -> None:
        """Refresh all translatable texts (called on language change)."""
        self.setTitle(t("input.source"))
        self._radio_remote.setText(t("input.remote_dataset"))
        self._radio_local.setText(t("input.local_file"))
        self._btn_file.setText(t("input.select_file"))
        self._btn_legend_preview.setToolTip(t("input.legend_preview"))
        self._download_box.setTitle(t("input.download_data"))
        self._btn_open_link.setText(t("input.open_download_page"))
