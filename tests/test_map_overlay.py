import numpy as np
from rasterio.transform import from_origin
from pyproj import CRS

from luma.gui.widgets.map_viewer import MapViewer
from luma.core.aoi import AOI
from shapely.geometry import Polygon


def test_classified_overlay_contains_transparent_invalid_pixels():
    data = np.array([[1, 2], [2, 1]], dtype=np.uint8)
    valid = np.array([[True, True], [True, False]])
    html = MapViewer._build_classified_overlay_html(
        data,
        valid,
        from_origin(-48.2, -21.7, 0.01, 0.01),
        CRS.from_epsg(4326),
        {1: "#008000", 2: "#ff0000"},
    )
    assert "L.imageOverlay" in html
    assert "data:image/png;base64," in html


def test_compare_aoi_map_uses_exact_geojson_polygons():
    aoi = AOI(Polygon([(-47, -22), (-47, -21), (-46, -21), (-47, -22)]))
    html = MapViewer._build_compare_aois_html([{"label": "Área 1", "aoi": aoi}])
    assert "L.geoJSON" in html
    assert '"type": "Polygon"' in html
    assert "Área 1" in html
