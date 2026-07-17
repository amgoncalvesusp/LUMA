"""Reusable help-bubble widget — the ⓘ button that opens a full-text popup."""

from PySide6.QtWidgets import (
    QPushButton, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame,
    QApplication, QScrollArea,
)
from PySide6.QtCore import Qt, QPoint, QEvent
from PySide6.QtGui import QGuiApplication

from luma.i18n.translator import t


def _as_html(text: str) -> str:
    """Wrap plain text in minimal HTML so Qt renders it with word wrap."""
    if "<" in text and ">" in text:
        return text  # already HTML
    return text.replace("\n", "<br>")


class _HelpPopup(QFrame):
    """Frameless popup that shows the full help text with word-wrap.

    Unlike QToolTip, this guarantees the text is never truncated:
    it uses a QLabel with wordWrap + a QScrollArea fallback if the
    text exceeds the available screen height.
    """

    def __init__(self, text: str, anchor: QWidget):
        super().__init__(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame { background: #2c3e50; border: 1px solid #34495e; border-radius: 6px; }"
            "QLabel { color: white; font-size: 12px; background: transparent; }"
            "QScrollArea { border: none; background: transparent; }"
        )

        label = QLabel(_as_html(text))
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        label.setOpenExternalLinks(True)
        label.setContentsMargins(10, 8, 10, 8)

        # Fixed content width so wordWrap computes a real height
        screen = QGuiApplication.screenAt(anchor.mapToGlobal(QPoint(0, 0))) \
            or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        content_w = min(440, max(260, geo.width() // 3))
        label.setFixedWidth(content_w)
        label.adjustSize()

        max_h = geo.height() - 80
        if label.sizeHint().height() > max_h:
            scroll = QScrollArea(self)
            scroll.setWidgetResizable(True)
            scroll.setWidget(label)
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(scroll)
            self.resize(content_w + 24, max_h)
        else:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(label)
            self.adjustSize()

        # Position next to anchor, keeping inside the screen
        target = anchor.mapToGlobal(QPoint(anchor.width() + 6, 0))
        if target.x() + self.width() > geo.right():
            target.setX(max(geo.left() + 4, anchor.mapToGlobal(QPoint(0, 0)).x() - self.width() - 6))
        if target.y() + self.height() > geo.bottom():
            target.setY(max(geo.top() + 4, geo.bottom() - self.height() - 4))
        self.move(target)


class HelpBubble(QPushButton):
    """Small circular ⓘ button that opens a full-text popup on click/hover."""

    def __init__(self, tooltip_text: str, parent: QWidget | None = None):
        super().__init__("i", parent)
        self._tip_text = tooltip_text
        self.setFixedSize(32, 32)
        # Short tooltip hint for hover; full content shown on click
        self.setToolTip(self._short_preview(tooltip_text))
        self.setCursor(Qt.CursorShape.WhatsThisCursor)
        # Override global QPushButton padding/min-height so the glyph stays centered
        self.setStyleSheet("""
            QPushButton {
                background-color: #176ca6;
                color: white;
                border: none;
                border-radius: 16px;
                padding: 0px;
                margin: 0px;
                min-width: 32px;
                min-height: 32px;
                max-width: 32px;
                max-height: 32px;
                font-family: "Segoe UI", "Arial", sans-serif;
                font-size: 13px;
                font-weight: bold;
                font-style: italic;
                qproperty-flat: true;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #125781;
            }
        """)
        self.clicked.connect(self._show_tip)
        self._popup: _HelpPopup | None = None

    @staticmethod
    def _short_preview(text: str) -> str:
        # First non-empty line, trimmed, to hint on hover; full text on click
        first = next((ln.strip() for ln in text.splitlines() if ln.strip()), text.strip())
        if len(first) > 120:
            first = first[:117] + "…"
        return first + "\n" + t("common.click_for_more")

    def _show_tip(self) -> None:
        if self._popup is not None:
            self._popup.close()
        self._popup = _HelpPopup(self._tip_text, self)
        self._popup.show()

    def set_tip(self, text: str) -> None:
        self._tip_text = text
        self.setToolTip(self._short_preview(text))


def labeled_input_with_help(
    label_text: str,
    widget: QWidget,
    help_text: str,
    parent: QWidget | None = None,
) -> tuple[QHBoxLayout, QLabel, HelpBubble]:
    """Create a horizontal layout: [Label] [Widget] [ⓘ].

    Returns (layout, label_widget, help_bubble) so callers can update texts.
    """
    layout = QHBoxLayout()
    lbl = QLabel(label_text)
    lbl.setMinimumWidth(100)
    bubble = HelpBubble(help_text, parent)
    layout.addWidget(lbl)
    layout.addWidget(widget, stretch=1)
    layout.addWidget(bubble)
    return layout, lbl, bubble
