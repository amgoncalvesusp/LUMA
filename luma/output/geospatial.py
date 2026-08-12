"""GIS exports for comparison points and their WGS-84 buffers."""

from __future__ import annotations

import math
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

import shapefile
from pyproj import CRS
from shapely.geometry import shape

from luma.core.buffer import buffer_geojson


WGS84 = CRS.from_epsg(4326)
_KML_NS = "http://www.opengis.net/kml/2.2"
ElementTree.register_namespace("", _KML_NS)


@dataclass(frozen=True)
class ExportPoint:
    """Validated point record used by all geospatial writers."""

    name: str
    lat: float
    lon: float
    radius_m: float


def _point_value(point, name: str, fallback: str | None = None):
    if isinstance(point, dict):
        value = point.get(name)
        if value is None and fallback:
            value = point.get(fallback)
        return value
    value = getattr(point, name, None)
    if value is None and fallback:
        value = getattr(point, fallback, None)
    return value


def normalize_points(points) -> tuple[ExportPoint, ...]:
    """Validate comparison points at the export boundary."""
    normalized: list[ExportPoint] = []
    for index, point in enumerate(points, 1):
        name = str(_point_value(point, "name") or f"Point {index}").strip()
        lat = float(_point_value(point, "lat"))
        lon = float(_point_value(point, "lon"))
        radius = float(_point_value(point, "radius_m", "radius"))
        if not all(math.isfinite(value) for value in (lat, lon, radius)):
            raise ValueError("Point coordinates and radius must be finite numbers")
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError(f"Point {name!r} is outside WGS-84 bounds")
        if radius <= 0:
            raise ValueError(f"Point {name!r} must have a positive radius")
        normalized.append(ExportPoint(name, lat, lon, radius))
    if not normalized:
        raise ValueError("At least one point is required for geospatial export")
    return tuple(normalized)


def _buffer_ring(point: ExportPoint) -> list[tuple[float, float]]:
    geometry = shape(buffer_geojson(point.lon, point.lat, point.radius_m))
    return [(float(x), float(y)) for x, y in geometry.exterior.coords]


def _kml_element(tag: str, text: str | None = None, parent=None):
    element = ElementTree.SubElement(parent, f"{{{_KML_NS}}}{tag}") if parent is not None else ElementTree.Element(f"{{{_KML_NS}}}{tag}")
    if text is not None:
        element.text = text
    return element


def _build_kml(points: tuple[ExportPoint, ...]) -> bytes:
    root = _kml_element("kml")
    document = _kml_element("Document", parent=root)
    _kml_element("name", "LUMA points and buffers", parent=document)

    point_style = _kml_element("Style", parent=document)
    point_style.set("id", "lumaPoint")
    icon_style = _kml_element("IconStyle", parent=point_style)
    _kml_element("color", "ff0000ff", parent=icon_style)
    _kml_element("scale", "1.0", parent=icon_style)

    buffer_style = _kml_element("Style", parent=document)
    buffer_style.set("id", "lumaBuffer")
    line_style = _kml_element("LineStyle", parent=buffer_style)
    _kml_element("color", "ff0000ff", parent=line_style)
    _kml_element("width", "2", parent=line_style)
    poly_style = _kml_element("PolyStyle", parent=buffer_style)
    _kml_element("color", "4d0000ff", parent=poly_style)

    for point in points:
        point_placemark = _kml_element("Placemark", parent=document)
        _kml_element("name", point.name, parent=point_placemark)
        _kml_element("styleUrl", "#lumaPoint", parent=point_placemark)
        point_geometry = _kml_element("Point", parent=point_placemark)
        _kml_element("coordinates", f"{point.lon:.10f},{point.lat:.10f},0", parent=point_geometry)

        buffer_placemark = _kml_element("Placemark", parent=document)
        _kml_element("name", f"{point.name} buffer", parent=buffer_placemark)
        _kml_element("styleUrl", "#lumaBuffer", parent=buffer_placemark)
        polygon = _kml_element("Polygon", parent=buffer_placemark)
        _kml_element("tessellate", "1", parent=polygon)
        outer = _kml_element("outerBoundaryIs", parent=polygon)
        ring = _kml_element("LinearRing", parent=outer)
        coordinates = " ".join(f"{x:.10f},{y:.10f},0" for x, y in _buffer_ring(point))
        _kml_element("coordinates", coordinates, parent=ring)

    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


def _write_prj(stem: Path) -> Path:
    path = stem.with_suffix(".prj")
    path.write_text(WGS84.to_wkt("WKT1_GDAL"), encoding="utf-8")
    return path


def _write_shapefiles(directory: Path, points: tuple[ExportPoint, ...]) -> dict[str, Path]:
    point_stem = directory / "points"
    point_writer = shapefile.Writer(str(point_stem), shapeType=shapefile.POINT, encoding="utf-8")
    point_writer.field("name", "C", size=254)
    point_writer.field("lat", "F", decimal=8)
    point_writer.field("lon", "F", decimal=8)
    point_writer.field("radius_m", "F", decimal=2)
    for point in points:
        point_writer.point(point.lon, point.lat)
        point_writer.record(point.name, point.lat, point.lon, point.radius_m)
    point_writer.close()

    buffer_stem = directory / "buffers"
    buffer_writer = shapefile.Writer(str(buffer_stem), shapeType=shapefile.POLYGON, encoding="utf-8")
    buffer_writer.field("name", "C", size=254)
    buffer_writer.field("radius_m", "F", decimal=2)
    for point in points:
        buffer_writer.poly([_buffer_ring(point)])
        buffer_writer.record(point.name, point.radius_m)
    buffer_writer.close()

    outputs = {
        "points_shp": point_stem.with_suffix(".shp"),
        "buffers_shp": buffer_stem.with_suffix(".shp"),
        "points_prj": _write_prj(point_stem),
        "buffers_prj": _write_prj(buffer_stem),
    }
    for stem in (point_stem, buffer_stem):
        stem.with_suffix(".cpg").write_text("UTF-8", encoding="ascii")
    return outputs


def export_points_buffers(directory: str | Path, points) -> dict[str, Path]:
    """Write KML/KMZ and separate point/buffer Shapefiles in WGS-84.

    The returned mapping contains the paths written to *directory*.  The
    point and polygon Shapefiles are separate layers so QGIS can style them
    independently while the KML/KMZ can be opened directly in Google Earth.
    """
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    normalized = normalize_points(points)
    kml_bytes = _build_kml(normalized)
    kml_path = target / "points_buffers.kml"
    kml_path.write_bytes(kml_bytes)
    kmz_path = target / "points_buffers.kmz"
    with zipfile.ZipFile(kmz_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("doc.kml", kml_bytes)
    outputs = {"kml": kml_path, "kmz": kmz_path}
    outputs.update(_write_shapefiles(target, normalized))
    return outputs
