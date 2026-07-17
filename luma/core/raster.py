"""Raster I/O — open local files and remote COGs, clip to buffer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.crs import CRS as RioCRS
from rasterio.mask import mask as rio_mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.transform import Affine
from pyproj import Geod
from pyproj import CRS
from shapely.geometry import Polygon, mapping
from shapely.geometry.base import BaseGeometry

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
        valid_mask: np.ndarray | None = None,
    ):
        self.data = data
        self.transform = transform
        self.crs = crs
        self.nodata = nodata
        self.pixel_area_m2 = pixel_area_m2
        if valid_mask is not None:
            if valid_mask.shape != data.shape:
                raise ValueError(
                    f"valid_mask shape {valid_mask.shape} does not match data shape {data.shape}"
                )
            if valid_mask.dtype != bool:
                raise ValueError("valid_mask must have boolean dtype")
        self._explicit_valid_mask = valid_mask

    @property
    def valid_mask(self) -> np.ndarray:
        """Boolean mask of valid (non-nodata) pixels."""
        if self._explicit_valid_mask is not None:
            return self._explicit_valid_mask
        if self.nodata is None:
            return np.ones(self.data.shape, dtype=bool)
        return self.data != self.nodata

    def valid_mask_for_legend(self, legend: dict[int, dict]) -> np.ndarray:
        """Return a mask that preserves class zero when declared by *legend*.

        Some products encode NoData as zero while others use zero as a real
        class (notably Dynamic World water).  The raster mask is authoritative
        when supplied by GDAL; for legacy rasters with only a nodata value,
        class zero is retained when the selected legend explicitly declares it.
        """
        mask = self.valid_mask.copy()
        if self._explicit_valid_mask is None and self.nodata == 0 and 0 in legend:
            mask |= self.data == 0
        return mask

    @property
    def total_pixels(self) -> int:
        return int(self.valid_mask.sum())


def pixel_area_m2_from_transform(
    transform: Affine, crs: CRS, *, latitude: float | None = None
) -> float:
    """Estimate one-pixel area in square metres from an affine transform.

    Projected CRS values use the affine determinant (which also handles
    rotated grids).  Geographic grids use a geodesic quadrilateral at the
    supplied latitude, or the transform's centre latitude when omitted.
    """
    if not crs:
        raise ValueError("A CRS is required to calculate pixel area")
    if not crs.is_geographic:
        return abs(float(transform.a * transform.e - transform.b * transform.d))

    # Pick the centre latitude of a representative pixel.  The exact location
    # only affects the tiny variation in longitude degree length.
    if latitude is None:
        _, y0 = transform * (0.5, 0.5)
        latitude = float(y0)
    x0, y0 = transform * (0, 0)
    x1, y1 = transform * (1, 0)
    x2, y2 = transform * (1, 1)
    x3, y3 = transform * (0, 1)
    # For north-up grids the corners above are sufficient.  If a transform is
    # anchored away from the requested latitude, shift only the geodesic
    # longitude scale by evaluating at the pixel's actual coordinates.
    del latitude  # retained in the signature for backwards-compatible calls
    geod = Geod(ellps="WGS84")
    area, _ = geod.polygon_area_perimeter([x0, x1, x2, x3], [y0, y1, y2, y3])
    return abs(float(area))


def align_raster_to_reference(
    source: RasterData,
    reference: RasterData,
    *,
    resampling: Resampling = Resampling.nearest,
) -> RasterData:
    """Reproject/resample *source* onto the exact grid of *reference*.

    Temporal comparisons must use identical CRS, transform, shape and pixel
    footprint.  This helper makes that invariant explicit and carries the
    reprojected validity mask alongside the values.
    """
    if source.data.ndim != 2 or reference.data.ndim != 2:
        raise ValueError("Only single-band 2-D rasters can be aligned")
    dst_shape = reference.data.shape
    source_mask = source.valid_mask
    same_grid = (
        source.data.shape == dst_shape
        and source.crs == reference.crs
        and source.transform == reference.transform
    )
    if same_grid:
        return RasterData(
            data=source.data.copy(),
            transform=reference.transform,
            crs=reference.crs,
            nodata=source.nodata,
            pixel_area_m2=reference.pixel_area_m2,
            valid_mask=source_mask.copy(),
        )

    fill_value = source.nodata if source.nodata is not None else 0
    destination = np.full(dst_shape, fill_value, dtype=source.data.dtype)
    reproject(
        source=source.data,
        destination=destination,
        src_transform=source.transform,
        src_crs=source.crs,
        src_nodata=source.nodata,
        dst_transform=reference.transform,
        dst_crs=reference.crs,
        dst_nodata=fill_value,
        resampling=resampling,
    )
    valid_destination = np.zeros(dst_shape, dtype=np.uint8)
    reproject(
        source=source_mask.astype(np.uint8),
        destination=valid_destination,
        src_transform=source.transform,
        src_crs=source.crs,
        src_nodata=0,
        dst_transform=reference.transform,
        dst_crs=reference.crs,
        dst_nodata=0,
        resampling=Resampling.nearest,
    )
    return RasterData(
        data=destination,
        transform=reference.transform,
        crs=reference.crs,
        nodata=fill_value,
        pixel_area_m2=reference.pixel_area_m2,
        valid_mask=valid_destination.astype(bool),
    )


def align_raster_pair(
    first: RasterData,
    second: RasterData,
    *,
    resampling: Resampling = Resampling.nearest,
) -> tuple[RasterData, RasterData]:
    """Return two rasters on a common grid (the first raster's grid)."""
    reference = RasterData(
        data=first.data.copy(), transform=first.transform, crs=first.crs,
        nodata=first.nodata, pixel_area_m2=first.pixel_area_m2,
        valid_mask=first.valid_mask.copy(),
    )
    return reference, align_raster_to_reference(second, reference, resampling=resampling)

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
    source_nodata = ds.nodata

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
            filled=False,
            indexes=band,
        )
    finally:
        ds.close()

    if out_image.ndim == 3:
        out_image = out_image[0]
    explicit_valid_mask = ~np.ma.getmaskarray(out_image)
    out_image = np.ma.getdata(out_image)
    pixel_area = pixel_area_m2_from_transform(
        out_transform, raster_crs, latitude=lat
    )

    return RasterData(
        data=out_image,
        transform=out_transform,
        crs=raster_crs,
        nodata=source_nodata,
        pixel_area_m2=pixel_area,
        valid_mask=explicit_valid_mask,
    )


def clip_raster_to_geometry(
    source: str | Path,
    geometry: BaseGeometry | object,
    geometry_crs: CRS | str | int | None = None,
    band: int = 1,
) -> RasterData:
    """Read a raster clipped to an arbitrary polygon or multipolygon.

    ``geometry`` can be a Shapely geometry or an ``luma.core.aoi.AOI``;
    an AOI carries its CRS, while plain geometries default to WGS-84.
    """
    if hasattr(geometry, "geometry") and hasattr(geometry, "crs"):
        geometry_crs = getattr(geometry, "crs")
        geometry = getattr(geometry, "geometry")
    if not isinstance(geometry, BaseGeometry) or geometry.is_empty:
        raise ValueError("AOI geometry must be a non-empty Shapely geometry")
    if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError("AOI geometry must be a polygon or multipolygon")

    source_crs = CRS.from_user_input(geometry_crs or "EPSG:4326")
    ds = open_raster(source)
    try:
        raster_crs = CRS.from_user_input(ds.crs)
        if raster_crs != source_crs:
            from luma.core.crs_utils import make_transformer
            from shapely.ops import transform as shapely_transform

            transformer = make_transformer(source_crs, raster_crs)
            clip_geometry = shapely_transform(
                lambda x, y, z=None: transformer.transform(x, y), geometry
            )
        else:
            clip_geometry = geometry
        out_image, out_transform = rio_mask(
            ds,
            [mapping(clip_geometry)],
            crop=True,
            filled=False,
            indexes=band,
        )
        source_nodata = ds.nodata
    finally:
        ds.close()

    if out_image.ndim == 3:
        out_image = out_image[0]
    explicit_valid_mask = ~np.ma.getmaskarray(out_image)
    out_image = np.ma.getdata(out_image)
    centre_lat = None
    if raster_crs.is_geographic:
        centre = geometry.centroid
        if source_crs != CRS.from_epsg(4326):
            from luma.core.crs_utils import make_transformer

            centre = make_transformer(source_crs, CRS.from_epsg(4326)).transform(
                centre.x, centre.y
            )
            centre_lat = centre[1]
        else:
            centre_lat = centre.y
    pixel_area = pixel_area_m2_from_transform(
        out_transform, raster_crs, latitude=centre_lat
    )
    return RasterData(
        data=out_image,
        transform=out_transform,
        crs=raster_crs,
        nodata=source_nodata,
        pixel_area_m2=pixel_area,
        valid_mask=explicit_valid_mask,
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
