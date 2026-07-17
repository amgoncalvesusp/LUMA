"""Coordinate input widget with validation."""

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QDoubleSpinBox


class CoordInput(QDoubleSpinBox):
    """Numeric input for latitude or longitude with validation and styling."""

    def __init__(
        self,
        min_val: float = -180.0,
        max_val: float = 180.0,
        default: float = 0.0,
        decimals: int = 6,
        suffix: str = "°",
    ):
        super().__init__()
        # Force period (".") as decimal separator regardless of OS locale
        self.setLocale(QLocale(QLocale.Language.C))
        self.setRange(min_val, max_val)
        self.setDecimals(decimals)
        self.setValue(default)
        self.setSuffix(suffix)
        self.setMinimumWidth(160)
        self.setStyleSheet("""
            QDoubleSpinBox {
                padding: 4px 8px;
                font-size: 13px;
            }
        """)


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
