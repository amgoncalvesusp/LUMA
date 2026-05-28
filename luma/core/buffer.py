"""Buffer geometry creation from coordinates and radius."""

from pyproj import CRS
from shapely.geometry import Point, Polygon, mapping
from shapely.ops import transform as shapely_transform

from luma.core.crs_utils import optimal_utm_crs, make_transformer


def create_buffer(
    lon: float,
    lat: float,
    radius_m: float,
    resolution: int = 128,
) -> tuple[Polygon, CRS]:
    """Create a circular buffer around a WGS-84 point.

    Parameters
    ----------
    lon, lat : float
        Centre coordinate in WGS-84 decimal degrees.
    radius_m : float
        Buffer radius in **metres**.
    resolution : int
        Number of segments used to approximate the circle.

    Returns
    -------
    (polygon, utm_crs) : tuple
        The buffer polygon in UTM coordinates and the UTM CRS used.
    """
    if not (-180 <= lon <= 180):
        raise ValueError(f"Longitude {lon} out of range [-180, 180]")
    if not (-90 <= lat <= 90):
        raise ValueError(f"Latitude {lat} out of range [-90, 90]")
    if radius_m <= 0:
        raise ValueError(f"Radius must be positive, got {radius_m}")

    utm_crs = optimal_utm_crs(lon, lat)
    wgs84 = CRS.from_epsg(4326)

    to_utm = make_transformer(wgs84, utm_crs)
    x, y = to_utm.transform(lon, lat)

    buffer_utm = Point(x, y).buffer(radius_m, resolution=resolution)
    return buffer_utm, utm_crs


def buffer_to_wgs84(buffer_geom: Polygon, utm_crs: CRS) -> Polygon:
    """Reproject a buffer polygon back to WGS-84."""
    to_wgs = make_transformer(utm_crs, CRS.from_epsg(4326))

    def _reproject(x, y, z=None):
        return to_wgs.transform(x, y)

    return shapely_transform(_reproject, buffer_geom)


def buffer_bounds_wgs84(
    lon: float, lat: float, radius_m: float
) -> tuple[float, float, float, float]:
    """Return the WGS-84 bounding box (west, south, east, north) of a buffer."""
    buf_utm, utm_crs = create_buffer(lon, lat, radius_m)
    buf_wgs = buffer_to_wgs84(buf_utm, utm_crs)
    return buf_wgs.bounds


def buffer_geojson(lon: float, lat: float, radius_m: float) -> dict:
    """Return GeoJSON dict for the buffer in WGS-84."""
    buf_utm, utm_crs = create_buffer(lon, lat, radius_m)
    buf_wgs = buffer_to_wgs84(buf_utm, utm_crs)
    return mapping(buf_wgs)


def buffer_area_km2(radius_m: float) -> float:
    """Theoretical area of the circular buffer in km²."""
    import math
    return math.pi * (radius_m / 1000) ** 2
