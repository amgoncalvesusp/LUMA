"""Coordinate input widget with validation and paste-friendly handling."""

import re

from PySide6.QtCore import QLocale, QObject, QEvent, Signal
from PySide6.QtGui import QKeySequence, QGuiApplication
from PySide6.QtWidgets import QDoubleSpinBox


_NUM_RE = re.compile(r"[-+]?\d+(?:[.,]\d+)?")


def _parse_coord_text(raw: str) -> list[float]:
    """Pull numeric values from a free-form coord string. Tolerates ',' or '.'."""
    if not raw:
        return []
    s = raw.strip().strip("()[]")
    # Drop degree, N/S/E/W markers
    s = s.replace("°", " ").replace("º", " ")
    s = re.sub(r"[NSEWnsew]", " ", s)
    out: list[float] = []
    for m in _NUM_RE.findall(s):
        try:
            out.append(float(m.replace(",", ".")))
        except ValueError:
            pass
    return out


class CoordInput(QDoubleSpinBox):
    """Numeric input for latitude/longitude/radius. Tolerates pasted strings."""

    pair_pasted = Signal(float, float)  # lat, lon when a pair is pasted

    def __init__(
        self,
        min_val: float = -180.0,
        max_val: float = 180.0,
        default: float = 0.0,
        decimals: int = 6,
        suffix: str = "°",
    ):
        super().__init__()
        self.setLocale(QLocale(QLocale.Language.C))
        self.setRange(min_val, max_val)
        self.setDecimals(decimals)
        self.setValue(default)
        self.setSuffix(suffix)
        self.setMinimumWidth(160)
        self.setStyleSheet("QDoubleSpinBox { padding: 4px 8px; font-size: 13px; }")
        # Allow keyboard tracking + paste via lineEdit
        le = self.lineEdit()
        le.installEventFilter(self)

    def valueFromText(self, text: str) -> float:
        nums = _parse_coord_text(text)
        if nums:
            return max(self.minimum(), min(self.maximum(), nums[0]))
        try:
            return float(text.replace(",", "."))
        except ValueError:
            return self.value()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress and event.matches(QKeySequence.StandardKey.Paste):
            cb = QGuiApplication.clipboard()
            raw = cb.text()
            nums = _parse_coord_text(raw)
            if len(nums) >= 2:
                lat = max(-90.0, min(90.0, nums[0]))
                lon = max(-180.0, min(180.0, nums[1]))
                self.pair_pasted.emit(lat, lon)
                # Set first value into this field too (latitude semantics)
                self.setValue(max(self.minimum(), min(self.maximum(), nums[0])))
                return True
            if len(nums) == 1:
                self.setValue(max(self.minimum(), min(self.maximum(), nums[0])))
                return True
        return super().eventFilter(obj, event)


class LatitudeInput(CoordInput):
    def __init__(self, default: float = 0.0):
        super().__init__(min_val=-90.0, max_val=90.0, default=default)


class LongitudeInput(CoordInput):
    def __init__(self, default: float = 0.0):
        super().__init__(min_val=-180.0, max_val=180.0, default=default)


class RadiusInput(CoordInput):
    def __init__(self, default: float = 5000.0):
        super().__init__(
            min_val=100.0,
            max_val=500_000.0,
            default=default,
            decimals=0,
            suffix=" m",
        )
        self.setSingleStep(500)
