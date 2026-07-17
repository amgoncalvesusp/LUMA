"""Area-of-interest geometry model and vector-file import helpers.

The rest of LUMA works with WGS-84 coordinates for user-facing geometries.  The
``AOI`` model keeps the source CRS explicit, validates polygonal input at the
boundary, and provides safe conversion to WGS-84 for maps and raster clipping.
"""

from __future__ import annotations

import json
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree

from pyproj import CRS, Geod
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform, unary_union

from luma.core.crs_utils import make_transformer


WGS84 = CRS.from_epsg(4326)
_GEOD = Geod(ellps="WGS84")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _as_geometry(value: Any) -> BaseGeometry:
    if isinstance(value, BaseGeometry):
        return value
    if not isinstance(value, dict):
        raise ValueError("GeoJSON geometry must be an object")
    if value.get("type") == "Feature":
        value = value.get("geometry")
    if not value:
        raise ValueError("GeoJSON feature has no geometry")
    try:
        return shape(value)
    except Exception as exc:
        raise ValueError("Invalid GeoJSON geometry") from exc


def _polygonal(geometry: BaseGeometry) -> Polygon | MultiPolygon:
    """Return the polygonal part of a geometry, or raise a useful error."""
    if not isinstance(geometry, BaseGeometry):
        raise ValueError("AOI geometry must be a Shapely polygon")
    if geometry.is_empty:
        raise ValueError("AOI polygon geometry is empty")
    if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        if geometry.geom_type == "GeometryCollection":
            polygons = [g for g in geometry.geoms if g.geom_type in {"Polygon", "MultiPolygon"}]
            if polygons:
                geometry = unary_union(polygons)
        if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
            raise ValueError("AOI geometry must be a polygon or multipolygon")
    if geometry.is_empty or not geometry.is_valid:
        raise ValueError("AOI polygon is invalid")
    return geometry


def _crs_from_geojson(data: dict, explicit: CRS | str | int | None) -> CRS:
    if explicit is not None:
        return CRS.from_user_input(explicit)
    crs_data = data.get("crs")
    if isinstance(crs_data, dict):
        props = crs_data.get("properties", {})
        value = props.get("name") or props.get("href")
        if value:
            try:
                return CRS.from_user_input(value)
            except Exception:
                pass
    return WGS84


@dataclass(frozen=True)
class AOI:
    """Validated polygonal area of interest.

    ``geometry`` is expressed in ``crs``.  GeoJSON export always returns a
    WGS-84 geometry, which is the convention used by Leaflet and user input.
    """

    geometry: Polygon | MultiPolygon
    crs: CRS | str | int = WGS84
    name: str = ""
    source: str = "manual"

    def __post_init__(self) -> None:
        crs = CRS.from_user_input(self.crs)
        geometry = _polygonal(self.geometry)
        object.__setattr__(self, "crs", crs)
        object.__setattr__(self, "geometry", geometry)
        if crs.is_geographic:
            wgs = geometry
        else:
            wgs = self._transform(WGS84).geometry
        west, south, east, north = wgs.bounds
        if not (-180 <= west <= 180 and -180 <= east <= 180):
            raise ValueError("AOI longitude is outside [-180, 180]")
        if not (-90 <= south <= 90 and -90 <= north <= 90):
            raise ValueError("AOI latitude is outside [-90, 90]")

    @classmethod
    def from_geojson(cls, value: dict | str | Path, *, crs: CRS | str | int | None = None, name: str = "") -> "AOI":
        data = _read_json(value)
        source_name = name or str(data.get("properties", {}).get("name", ""))
        if data.get("type") == "FeatureCollection":
            geoms = [_as_geometry(feature) for feature in data.get("features", [])]
            if not geoms:
                raise ValueError("GeoJSON FeatureCollection contains no features")
            geometry = unary_union(geoms)
            source_name = name or source_name
        else:
            geometry = _as_geometry(data)
        return cls(geometry=_polygonal(geometry), crs=_crs_from_geojson(data, crs), name=source_name, source="geojson")

    @classmethod
    def from_kml(cls, value: str | Path, *, name: str = "") -> "AOI":
        geometry, parsed_name = parse_kml(value)
        return cls(geometry=geometry, crs=WGS84, name=name or parsed_name, source="kml")

    @classmethod
    def from_file(cls, path: str | Path, *, crs: CRS | str | int | None = None) -> "AOI":
        return load_aoi(path, crs=crs)

    def _transform(self, target: CRS | str | int) -> "AOI":
        target_crs = CRS.from_user_input(target)
        if target_crs == self.crs:
            return self
        transformer = make_transformer(self.crs, target_crs)
        projected = transform(lambda x, y, z=None: transformer.transform(x, y), self.geometry)
        return AOI(projected, target_crs, self.name, self.source)

    def to_wgs84(self) -> "AOI":
        return self._transform(WGS84)

    def to_geojson(self) -> dict:
        from shapely.geometry import mapping

        return mapping(self.to_wgs84().geometry)

    @property
    def bounds_wgs84(self) -> tuple[float, float, float, float]:
        return self.to_wgs84().geometry.bounds

    @property
    def centroid_wgs84(self) -> tuple[float, float]:
        point = self.to_wgs84().geometry.centroid
        return point.y, point.x

    @property
    def area_m2(self) -> float:
        wgs = self.to_wgs84().geometry
        area, _ = _GEOD.geometry_area_perimeter(wgs)
        return abs(area)

    @property
    def area_km2(self) -> float:
        return self.area_m2 / 1_000_000


def _read_json(value: dict | str | Path) -> dict:
    if isinstance(value, dict):
        return value
    is_path = isinstance(value, Path)
    if isinstance(value, str) and "{" not in value and len(value) < 4096:
        try:
            is_path = Path(value).exists()
        except OSError:
            is_path = False
    if is_path:
        path = Path(value)
        return json.loads(path.read_text(encoding="utf-8-sig"))
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid GeoJSON JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("GeoJSON root must be an object")
    return parsed


def _kml_coordinates(node: ElementTree.Element | None) -> list[tuple[float, float]]:
    if node is None or not (node.text or "").strip():
        raise ValueError("KML polygon ring has no coordinates")
    out: list[tuple[float, float]] = []
    for token in (node.text or "").replace("\n", " ").split():
        fields = token.split(",")
        if len(fields) < 2:
            continue
        out.append((float(fields[0]), float(fields[1])))
    if len(out) < 4:
        raise ValueError("KML polygon ring needs at least four coordinates")
    if out[0] != out[-1]:
        out.append(out[0])
    return out


def parse_kml(value: str | Path) -> tuple[Polygon | MultiPolygon, str]:
    """Parse Polygon elements from KML/KMZ without an optional GIS package."""
    is_path = isinstance(value, Path)
    if isinstance(value, str) and "<" not in value and len(value) < 4096:
        try:
            is_path = Path(value).exists()
        except OSError:
            is_path = False
    if is_path:
        path = Path(value)
        if path.suffix.lower() == ".kmz":
            with zipfile.ZipFile(path) as archive:
                name = next((n for n in archive.namelist() if n.lower().endswith(".kml")), None)
                if not name:
                    raise ValueError("KMZ archive does not contain a KML file")
                text = archive.read(name)
        else:
            text = path.read_bytes()
    else:
        text = str(value).encode("utf-8")
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        raise ValueError("Invalid KML document") from exc

    polygons: list[Polygon] = []
    names: list[str] = []
    for placemark in root.iter():
        if _local_name(placemark.tag) != "Placemark":
            continue
        name_node = next((n for n in placemark if _local_name(n.tag) == "name"), None)
        if name_node is not None and name_node.text:
            names.append(name_node.text.strip())
        for polygon_node in placemark.iter():
            if _local_name(polygon_node.tag) != "Polygon":
                continue
            outer_node = next((n for n in polygon_node.iter() if _local_name(n.tag) == "outerBoundaryIs"), None)
            outer_coords = next((n for n in outer_node.iter() if _local_name(n.tag) == "coordinates"), None) if outer_node is not None else None
            if outer_coords is None:
                raise ValueError("KML Polygon has no outer boundary")
            holes = []
            for inner in (n for n in polygon_node.iter() if _local_name(n.tag) == "innerBoundaryIs"):
                coords = next((n for n in inner.iter() if _local_name(n.tag) == "coordinates"), None)
                holes.append(_kml_coordinates(coords))
            polygons.append(Polygon(_kml_coordinates(outer_coords), holes))
    if not polygons:
        raise ValueError("KML contains no Polygon elements")
    geometry = _polygonal(unary_union(polygons))
    return geometry, (names[0] if names else "")


def _ring_depths(rings: list[list[tuple[float, float]]]) -> list[int]:
    polygons = [Polygon(ring) for ring in rings]
    depths: list[int] = []
    for i, polygon in enumerate(polygons):
        probe = polygon.representative_point()
        depths.append(sum(1 for j, other in enumerate(polygons) if i != j and other.area > polygon.area and other.contains(probe)))
    return depths


def _read_shp(path: Path) -> tuple[Polygon | MultiPolygon, CRS]:
    raw = path.read_bytes()
    if len(raw) < 100:
        raise ValueError("Invalid Shapefile header")
    offset = 100
    rings: list[list[tuple[float, float]]] = []
    while offset + 8 <= len(raw):
        _, length_words = struct.unpack_from(">2i", raw, offset)
        offset += 8
        end = offset + length_words * 2
        if end > len(raw):
            raise ValueError("Invalid Shapefile record length")
        shape_type = struct.unpack_from("<i", raw, offset)[0]
        if shape_type in (0,):
            offset = end
            continue
        if shape_type not in (5, 15, 25):
            raise ValueError("Shapefile must contain polygon features")
        num_parts, num_points = struct.unpack_from("<2i", raw, offset + 36)
        parts_start = offset + 44
        parts = list(struct.unpack_from(f"<{num_parts}i", raw, parts_start))
        points_start = parts_start + 4 * num_parts
        points = [struct.unpack_from("<2d", raw, points_start + 16 * i) for i in range(num_points)]
        for i, start in enumerate(parts):
            stop = parts[i + 1] if i + 1 < len(parts) else num_points
            ring = [(float(x), float(y)) for x, y in points[start:stop]]
            if len(ring) >= 4:
                if ring[0] != ring[-1]:
                    ring.append(ring[0])
                rings.append(ring)
        offset = end
    if not rings:
        raise ValueError("Shapefile contains no polygon records")
    depths = _ring_depths(rings)
    exteriors = [i for i, depth in enumerate(depths) if depth % 2 == 0]
    polygons = []
    for i in exteriors:
        holes = []
        for j, depth in enumerate(depths):
            if depth != depths[i] + 1:
                continue
            probe = Polygon(rings[j]).representative_point()
            if Polygon(rings[i]).contains(probe):
                holes.append(rings[j])
        polygons.append(Polygon(rings[i], holes))
    geometry = _polygonal(unary_union(polygons))
    prj = path.with_suffix(".prj")
    crs = WGS84
    if prj.exists():
        try:
            crs = CRS.from_wkt(prj.read_text(encoding="utf-8"))
        except Exception:
            raise ValueError("Shapefile .prj contains an invalid CRS")
    return geometry, crs


def load_aoi(value: AOI | dict | str | Path, *, crs: CRS | str | int | None = None) -> AOI:
    """Load an AOI from an ``AOI``, GeoJSON, KML/KMZ or polygon Shapefile."""
    if isinstance(value, AOI):
        return value
    if isinstance(value, dict):
        return AOI.from_geojson(value, crs=crs)
    path = Path(value)
    suffix = path.suffix.lower()
    if suffix in {".json", ".geojson"}:
        return AOI.from_geojson(path, crs=crs)
    if suffix in {".kml", ".kmz"}:
        return AOI.from_kml(path)
    if suffix == ".shp":
        geometry, source_crs = _read_shp(path)
        return AOI(geometry, crs or source_crs, source=str(path), name=path.stem)
    raise ValueError("Unsupported AOI format; use GeoJSON, KML, KMZ or Shapefile")
