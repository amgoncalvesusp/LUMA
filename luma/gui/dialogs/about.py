"""About dialog — credits, version, institution."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
)
from PySide6.QtCore import Qt

import luma
from luma.i18n.translator import t


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("about.title"))
        self.setFixedSize(420, 340)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Logo / title
        title = QLabel("LUMA")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        version = QLabel(t("about.version", version=luma.__version__))
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet("font-size: 13px; color: #7f8c8d;")
        layout.addWidget(version)

        desc = QLabel(t("about.description"))
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; margin: 8px 0;")
        layout.addWidget(desc)

        # Authors
        sep1 = QLabel("─" * 50)
        sep1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sep1.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(sep1)

        authors_title = QLabel(t("about.authors_label"))
        authors_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        authors_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(authors_title)

        for author in luma.__authors__:
            lbl = QLabel(author)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size: 12px;")
            layout.addWidget(lbl)

        inst = QLabel(f"\n{t('about.institution_label')}: {luma.__institution__}")
        inst.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inst.setStyleSheet("font-size: 12px; color: #555;")
        layout.addWidget(inst)

        lic = QLabel(f"{t('about.license_label')}: {t('about.license_value')}")
        lic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lic.setStyleSheet("font-size: 11px; color: #888; margin-top: 6px;")
        layout.addWidget(lic)

        # Close
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("OK")
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        btn_row.addStretch()
        layout.addLayout(btn_row)
