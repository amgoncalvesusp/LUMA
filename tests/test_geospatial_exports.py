from pathlib import Path
from zipfile import ZipFile

import shapefile
from pyproj import CRS

from luma.output.geospatial import export_points_buffers


def test_export_points_and_buffers_is_qgis_google_earth_ready(tmp_path: Path):
    outputs = export_points_buffers(
        tmp_path,
        [
            {"name": "Ponto Á", "lat": -23.55, "lon": -46.63, "radius_m": 500},
            {"name": "Ponto B", "lat": -23.56, "lon": -46.64, "radius_m": 750},
        ],
    )

    assert {path.suffix for path in outputs.values()} >= {".kml", ".kmz"}
    assert (tmp_path / "points.shp").exists()
    assert (tmp_path / "buffers.shp").exists()
    assert (tmp_path / "points.prj").exists()
    assert (tmp_path / "buffers.prj").exists()
    assert CRS.from_wkt((tmp_path / "points.prj").read_text()).to_epsg() == 4326
    assert CRS.from_wkt((tmp_path / "buffers.prj").read_text()).to_epsg() == 4326

    point_reader = shapefile.Reader(str(tmp_path / "points.shp"))
    buffer_reader = shapefile.Reader(str(tmp_path / "buffers.shp"))
    assert len(point_reader) == 2
    assert len(buffer_reader) == 2
    assert point_reader.shapeType == shapefile.POINT
    assert buffer_reader.shapeType == shapefile.POLYGON
    assert point_reader.record(0)[0] == "Ponto Á"

    kml_text = (tmp_path / "points_buffers.kml").read_text(encoding="utf-8")
    assert "Ponto Á" in kml_text
    assert "<Point>" in kml_text
    assert "<Polygon>" in kml_text
    with ZipFile(tmp_path / "points_buffers.kmz") as archive:
        assert "doc.kml" in archive.namelist()
        assert b"<Point>" in archive.read("doc.kml")
