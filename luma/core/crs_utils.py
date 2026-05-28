"""CRS utilities — automatic UTM zone detection and coordinate transforms."""

from pyproj import CRS, Transformer


def optimal_utm_crs(lon: float, lat: float) -> CRS:
    """Return the optimal UTM CRS for a given WGS-84 coordinate.

    Handles both hemispheres and the full longitude range including
    the antimeridian neighbourhood.
    """
    zone_number = int((lon + 180) / 6) + 1
    zone_number = max(1, min(60, zone_number))
    hemisphere = "north" if lat >= 0 else "south"
    epsg = 32600 + zone_number if hemisphere == "north" else 32700 + zone_number
    return CRS.from_epsg(epsg)


def make_transformer(src_crs: CRS, dst_crs: CRS) -> Transformer:
    """Create a thread-safe pyproj Transformer."""
    return Transformer.from_crs(src_crs, dst_crs, always_xy=True)


def reproject_point(lon: float, lat: float, dst_crs: CRS) -> tuple[float, float]:
    """Reproject a WGS-84 lon/lat point to *dst_crs* and return (x, y)."""
    transformer = make_transformer(CRS.from_epsg(4326), dst_crs)
    return transformer.transform(lon, lat)


def reproject_point_inverse(x: float, y: float, src_crs: CRS) -> tuple[float, float]:
    """Reproject a point from *src_crs* back to WGS-84 lon/lat."""
    transformer = make_transformer(src_crs, CRS.from_epsg(4326))
    return transformer.transform(x, y)
