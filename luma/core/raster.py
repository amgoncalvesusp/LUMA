"""Raster I/O — open local files and remote COGs, clip to buffer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.crs import CRS as RioCRS
from rasterio.mask import mask as rio_mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from pyproj import CRS
from shapely.geometry import Polygon, mapping

from luma.core.buffer import create_buffer, buffer_to_wgs84
from luma.core.crs_utils import optimal_utm_crs


class RasterData:
    """Container for clipped raster data and associated metadata."""

    def __init__(
        self,
        data: np.ndarray,
        transform: rasterio.Affine,
        crs: CRS,
        nodata: float | int | None,
        pixel_area_m2: float,
    ):
        self.data = data
        self.transform = transform
        self.crs = crs
        self.nodata = nodata
        self.pixel_area_m2 = pixel_area_m2

    @property
    def valid_mask(self) -> np.ndarray:
        """Boolean mask of valid (non-nodata) pixels."""
        if self.nodata is None:
            return np.ones(self.data.shape, dtype=bool)
        return self.data != self.nodata

    @property
    def total_pixels(self) -> int:
        return int(self.valid_mask.sum())


def open_raster(source: str | Path) -> rasterio.DatasetReader:
    """Open a raster file (local path or remote COG URL)."""
    source_str = str(source)
    env_options: dict[str, Any] = {}
    if source_str.startswith(("http://", "https://", "s3://")):
        env_options = {
            "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
            "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.tiff,.vrt",
            "GDAL_HTTP_TIMEOUT": "60",
            "GDAL_HTTP_MAX_RETRY": "3",
            "GDAL_HTTP_RETRY_DELAY": "5",
        }
    env = rasterio.Env(**env_options)
    env.__enter__()
    try:
        ds = rasterio.open(source_str)
    except Exception:
        env.__exit__(None, None, None)
        raise
    return ds


def clip_raster_to_buffer(
    source: str | Path,
    lon: float,
    lat: float,
    radius_m: float,
    band: int = 1,
) -> RasterData:
    """Read a raster source clipped to a circular buffer.

    The function handles CRS mismatches by reprojecting the buffer
    geometry to the raster's native CRS before clipping.
    """
    buf_utm, utm_crs = create_buffer(lon, lat, radius_m)

    ds = open_raster(source)
    raster_crs = CRS.from_user_input(ds.crs)

    # Reproject buffer to raster CRS for clipping
    if raster_crs != utm_crs:
        from luma.core.crs_utils import make_transformer
        from shapely.ops import transform as shapely_transform

        tr = make_transformer(utm_crs, raster_crs)
        buf_in_raster_crs = shapely_transform(
            lambda x, y, z=None: tr.transform(x, y), buf_utm
        )
    else:
        buf_in_raster_crs = buf_utm

    geojson_geom = mapping(buf_in_raster_crs)

    try:
        out_image, out_transform = rio_mask(
            ds,
            [geojson_geom],
            crop=True,
            filled=True,
            nodata=ds.nodata if ds.nodata is not None else 0,
            indexes=band,
        )
    finally:
        ds.close()

    if out_image.ndim == 3:
        out_image = out_image[0]

    nodata_val = ds.nodata if ds.nodata is not None else 0

    # Calculate pixel area in m² from the raster's resolution
    res_x = abs(out_transform.a)
    res_y = abs(out_transform.e)
    if raster_crs.is_geographic:
        import math
        mid_lat = math.radians(lat)
        m_per_deg_lon = 111_320 * math.cos(mid_lat)
        m_per_deg_lat = 110_540
        pixel_area = (res_x * m_per_deg_lon) * (res_y * m_per_deg_lat)
    else:
        pixel_area = res_x * res_y

    return RasterData(
        data=out_image,
        transform=out_transform,
        crs=raster_crs,
        nodata=nodata_val,
        pixel_area_m2=pixel_area,
    )


def get_raster_info(source: str | Path) -> dict:
    """Return basic metadata for a raster source."""
    ds = open_raster(source)
    info = {
        "width": ds.width,
        "height": ds.height,
        "crs": str(ds.crs),
        "bounds": ds.bounds,
        "resolution": ds.res,
        "nodata": ds.nodata,
        "dtype": str(ds.dtypes[0]),
        "band_count": ds.count,
    }
    ds.close()
    return info
