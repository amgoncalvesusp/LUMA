import json
import struct

import pytest
from shapely.geometry import Polygon

from luma.core.aoi import AOI, load_aoi, parse_kml


def test_geojson_feature_is_normalized_to_wgs84():
    aoi = AOI.from_geojson(
        {
            "type": "Feature",
            "properties": {"name": "campus"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-47.0, -23.0], [-46.99, -23.0], [-46.99, -22.99], [-47.0, -23.0]]],
            },
        }
    )
    assert aoi.name == "campus"
    assert aoi.crs.to_epsg() == 4326
    assert aoi.geometry.is_valid
    assert aoi.area_m2 > 0
    assert aoi.to_geojson()["type"] == "Polygon"


def test_feature_collection_unions_polygon_features():
    data = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {}, "geometry": {
                "type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]
            }},
            {"type": "Feature", "properties": {}, "geometry": {
                "type": "Polygon", "coordinates": [[[1, 0], [2, 0], [2, 1], [1, 0]]]
            }},
        ],
    }
    aoi = AOI.from_geojson(data)
    assert aoi.geometry.geom_type in {"Polygon", "MultiPolygon"}
    assert aoi.geometry.area > 0


def test_validation_rejects_non_polygon_and_out_of_range_coordinates():
    with pytest.raises(ValueError, match="polygon"):
        AOI(geometry=Polygon())
    with pytest.raises(ValueError, match="longitude"):
        AOI.from_geojson({"type": "Polygon", "coordinates": [[[181, 0], [182, 0], [181, 1], [181, 0]]]})


def test_kml_polygon_parser_supports_holes():
    kml = """<?xml version="1.0"?><kml xmlns="http://www.opengis.net/kml/2.2"><Placemark><name>Area</name><Polygon>
      <outerBoundaryIs><LinearRing><coordinates>0,0 3,0 3,3 0,3 0,0</coordinates></LinearRing></outerBoundaryIs>
      <innerBoundaryIs><LinearRing><coordinates>1,1 2,1 2,2 1,2 1,1</coordinates></LinearRing></innerBoundaryIs>
    </Polygon></Placemark></kml>"""
    geom, name = parse_kml(kml)
    assert name == "Area"
    assert geom.geom_type == "Polygon"
    assert len(geom.interiors) == 1


def test_load_aoi_accepts_geojson_path(tmp_path):
    path = tmp_path / "area.geojson"
    path.write_text(json.dumps({"type": "Point", "coordinates": [0, 0]}), encoding="utf-8")
    with pytest.raises(ValueError, match="polygon"):
        load_aoi(path)


def test_minimal_polygon_shapefile_loader(tmp_path):
    # One Polygon record with one clockwise ring (ESRI exterior convention).
    points = [(0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0), (0.0, 0.0)]
    content = struct.pack("<i4d2i", 5, 0.0, 0.0, 2.0, 1.0, 1, len(points))
    content += struct.pack("<i", 0)
    content += b"".join(struct.pack("<2d", *p) for p in points)
    header = bytearray(100)
    struct.pack_into(">i", header, 0, 9994)
    struct.pack_into(">i", header, 24, (100 + 8 + len(content)) // 2)
    struct.pack_into("<ii", header, 28, 1000, 5)
    struct.pack_into("<4d", header, 36, 0.0, 0.0, 2.0, 1.0)
    shp = tmp_path / "area.shp"
    shp.write_bytes(bytes(header) + struct.pack(">2i", 1, len(content) // 2) + content)
    aoi = load_aoi(shp)
    assert aoi.geometry.geom_type == "Polygon"
    assert round(aoi.geometry.area, 6) == 2
