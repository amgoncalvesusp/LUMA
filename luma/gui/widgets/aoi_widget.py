"""Qt widget for creating or importing an area of interest."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from shapely.geometry import Polygon

from luma.core.aoi import AOI, load_aoi
from luma.i18n.translator import t


class PolygonCanvas(QWidget):
    """Small dependency-free canvas that converts clicks to lon/lat vertices."""

    vertex_added = Signal(float, float)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.vertices: list[tuple[float, float]] = []
        self.drawing = False
        self._extent = (-180.0, -90.0, 180.0, 90.0)
        self.setMinimumSize(260, 150)
        self.setMouseTracking(True)

    def set_extent(self, bounds: tuple[float, float, float, float]) -> None:
        west, south, east, north = bounds
        dx = max((east - west) * 0.1, 0.01)
        dy = max((north - south) * 0.1, 0.01)
        self._extent = (west - dx, south - dy, east + dx, north + dy)
        self.update()

    def clear(self) -> None:
        self.vertices = []
        self.update()

    def _to_lonlat(self, point: QPointF) -> tuple[float, float]:
        west, south, east, north = self._extent
        x = max(0.0, min(float(self.width()), point.x()))
        y = max(0.0, min(float(self.height()), point.y()))
        lon = west + (east - west) * x / max(1.0, self.width())
        lat = north - (north - south) * y / max(1.0, self.height())
        return lon, lat

    def _to_pixel(self, lon: float, lat: float) -> QPointF:
        west, south, east, north = self._extent
        x = (lon - west) / (east - west) * self.width()
        y = (north - lat) / (north - south) * self.height()
        return QPointF(x, y)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt API
        if self.drawing and event.button() == Qt.MouseButton.LeftButton:
            lon, lat = self._to_lonlat(event.position())
            self.vertices.append((lon, lat))
            self.vertex_added.emit(lon, lat)
            self.update()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f2f5f7"))
        painter.setPen(QPen(QColor("#c5ced3"), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        if not self.vertices:
            painter.setPen(QColor("#61717a"))
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter, t("aoi.add_vertices")
            )
            return
        points = [self._to_pixel(lon, lat) for lon, lat in self.vertices]
        if len(points) >= 3:
            painter.setPen(QPen(QColor("#c0392b"), 2))
            painter.setBrush(QBrush(QColor(231, 76, 60, 55)))
            painter.drawPolygon(points)
        painter.setPen(QPen(QColor("#922b21"), 2))
        painter.setBrush(QBrush(QColor("#ffffff")))
        for point in points:
            painter.drawEllipse(point, 4, 4)


class AOIWidget(QWidget):
    """Draw, edit, clear, or import a polygon and emit a validated ``AOI``."""

    aoi_changed = Signal(object)
    error = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._aoi: AOI | None = None
        self.canvas = PolygonCanvas(self)
        self._status = QLabel(t("aoi.none"))
        self._status.setWordWrap(True)

        self.btn_draw = QPushButton(t("aoi.draw"))
        self.btn_finish = QPushButton(t("aoi.finish"))
        self.btn_import = QPushButton(t("aoi.import"))
        self.btn_clear = QPushButton(t("aoi.clear"))
        self.btn_finish.setEnabled(False)

        buttons = QGridLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.addWidget(self.btn_draw, 0, 0)
        buttons.addWidget(self.btn_finish, 0, 1)
        buttons.addWidget(self.btn_import, 1, 0)
        buttons.addWidget(self.btn_clear, 1, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        layout.addLayout(buttons)
        layout.addWidget(self._status)

        self.btn_draw.clicked.connect(self.start_drawing)
        self.btn_finish.clicked.connect(self.finish_drawing)
        self.btn_import.clicked.connect(self.import_file)
        self.btn_clear.clicked.connect(self.clear)
        self.canvas.vertex_added.connect(self._on_vertex_added)

    @property
    def aoi(self) -> AOI | None:
        return self._aoi

    def set_extent(self, bounds: tuple[float, float, float, float]) -> None:
        """Set the lon/lat viewport used when drawing manually."""
        self.canvas.set_extent(bounds)

    def start_drawing(self) -> None:
        self.canvas.clear()
        self.canvas.drawing = True
        self.btn_finish.setEnabled(False)
        self._status.setText(t("aoi.vertex_instruction"))

    def _on_vertex_added(self, lon: float, lat: float) -> None:
        del lon, lat
        self.btn_finish.setEnabled(len(self.canvas.vertices) >= 3)
        self._status.setText(t("aoi.vertex_count", n=len(self.canvas.vertices)))

    def finish_drawing(self) -> AOI | None:
        if len(self.canvas.vertices) < 3:
            self.error.emit(t("aoi.invalid_vertices"))
            return None
        vertices = list(self.canvas.vertices)
        vertices.append(vertices[0])
        try:
            aoi = AOI(Polygon(vertices), source="manual")
        except ValueError as exc:
            self.error.emit(str(exc))
            return None
        self._set_aoi(aoi)
        self.canvas.drawing = False
        return aoi

    def import_path(self, path: str | Path) -> AOI | None:
        try:
            aoi = load_aoi(path)
        except (OSError, ValueError) as exc:
            self.error.emit(str(exc))
            return None
        self._set_aoi(aoi)
        return aoi

    def set_aoi(self, aoi: AOI | None) -> None:
        """Restore an AOI from a project without opening a file dialog."""
        if aoi is None:
            self.clear()
        else:
            self._set_aoi(aoi)

    def import_file(self) -> AOI | None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("aoi.import_dialog"),
            "",
            "Vetores (*.geojson *.json *.kml *.kmz *.shp);;Todos os arquivos (*)",
        )
        return self.import_path(path) if path else None

    def _set_aoi(self, aoi: AOI) -> None:
        self._aoi = aoi
        self.canvas.vertices = [tuple(coord) for coord in list(aoi.to_wgs84().geometry.exterior.coords)] if aoi.to_wgs84().geometry.geom_type == "Polygon" else []
        self.canvas.set_extent(aoi.bounds_wgs84)
        self.canvas.update()
        area = aoi.area_m2 / 10_000
        self._status.setText(t("aoi.selected_area", area=area))
        self.aoi_changed.emit(aoi)

    def refresh_texts(self) -> None:
        """Refresh controls after the application language changes."""
        self.btn_draw.setText(t("aoi.draw"))
        self.btn_finish.setText(t("aoi.finish"))
        self.btn_import.setText(t("aoi.import"))
        self.btn_clear.setText(t("aoi.clear"))
        if self._aoi is None:
            self._status.setText(t("aoi.none"))
        else:
            self._status.setText(
                t("aoi.selected_area", area=self._aoi.area_m2 / 10_000)
            )
        self.canvas.update()

    def clear(self) -> None:
        self._aoi = None
        self.canvas.clear()
        self.canvas.drawing = False
        self.btn_finish.setEnabled(False)
        self._status.setText(t("aoi.none"))
        self.aoi_changed.emit(None)
