"""Dataset download manager with progress tracking and local caching."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Callable

import httpx

CACHE_DIR = Path.home() / ".luma" / "cache"


def get_cache_dir() -> Path:
    """Return (and create) the cache directory."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def cache_key(url: str, bounds: tuple) -> str:
    """Deterministic cache filename from URL and bounding box."""
    raw = f"{url}|{bounds}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"tile_{h}.tif"


def get_cached_path(url: str, bounds: tuple) -> Path | None:
    """Return cached file path if it exists, else None."""
    key = cache_key(url, bounds)
    path = get_cache_dir() / key
    return path if path.exists() else None


def download_cog_window(
    url: str,
    bounds: tuple[float, float, float, float],
    output_path: Path | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> Path:
    """Download a COG window (bounding box) to a local GeoTIFF.

    Uses rasterio with a windowed read to only fetch the relevant tiles.

    Parameters
    ----------
    url : str
        Remote COG URL (HTTP/S3).
    bounds : tuple
        (west, south, east, north) in the raster's native CRS.
    output_path : Path, optional
        Where to save.  Defaults to cache directory.
    progress_callback : callable, optional
        Called with (bytes_downloaded, total_bytes).

    Returns
    -------
    Path to the downloaded GeoTIFF.
    """
    import rasterio
    from rasterio.windows import from_bounds

    cached = get_cached_path(url, bounds)
    if cached is not None:
        return cached

    if output_path is None:
        output_path = get_cache_dir() / cache_key(url, bounds)

    env_options = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "GDAL_HTTP_TIMEOUT": "120",
        "GDAL_HTTP_MAX_RETRY": "3",
        "GDAL_HTTP_RETRY_DELAY": "5",
    }

    with rasterio.Env(**env_options):
        with rasterio.open(url) as src:
            window = from_bounds(*bounds, transform=src.transform)
            # Clamp window to dataset bounds
            window = window.intersection(
                rasterio.windows.Window(0, 0, src.width, src.height)
            )

            out_transform = rasterio.windows.transform(window, src.transform)
            out_meta = src.meta.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": int(window.height),
                "width": int(window.width),
                "transform": out_transform,
                "compress": "lzw",
            })

            with rasterio.open(output_path, "w", **out_meta) as dst:
                for band_idx in range(1, src.count + 1):
                    band_data = src.read(band_idx, window=window)
                    dst.write(band_data, band_idx)
                    if progress_callback:
                        progress_callback(band_idx, src.count)

    return output_path


def get_cache_size_mb() -> float:
    """Return total size of cached files in MB."""
    cache = get_cache_dir()
    total = sum(f.stat().st_size for f in cache.glob("*") if f.is_file())
    return total / (1024 * 1024)


def clear_cache() -> int:
    """Delete all cached files. Returns the number of files removed."""
    cache = get_cache_dir()
    count = 0
    for f in cache.glob("*"):
        if f.is_file():
            f.unlink()
            count += 1
    return count
