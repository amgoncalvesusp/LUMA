import numpy as np
from pyproj import CRS
from rasterio.transform import Affine

import luma.gui.main_window as main_window
from luma.core.raster import RasterData


def test_temporal_calculation_path_returns_transition(monkeypatch):
    legend = {
        1: {"name": "Forest", "color": "#008000"},
        2: {"name": "Urban", "color": "#ff0000"},
    }
    rasters = [
        RasterData(
            np.array([[1, 1], [2, 2]], dtype=np.uint8),
            Affine.scale(30, -30), CRS.from_epsg(3857), 255, 900.0,
        ),
        RasterData(
            np.array([[1, 2], [2, 2]], dtype=np.uint8),
            Affine.scale(30, -30), CRS.from_epsg(3857), 255, 900.0,
        ),
    ]
    monkeypatch.setattr(main_window, "load_legend_classes", lambda key: legend)
    monkeypatch.setattr(main_window, "clip_raster_to_buffer", lambda *args: rasters.pop(0))

    transition = main_window.MainWindow._compute_temporal_transition(
        "year-1.tif", "year-2.tif", "test", -23.55, -46.63, 500.0, None,
    )

    assert transition["matrix"][1][1] == 900.0
    assert transition["matrix"][1][2] == 900.0
    assert transition["persistence"] == 75.0
