"""Small provider facade for catalog-backed MapBiomas downloads.

The GUI can continue using :func:`luma.sources.catalog.resolve_remote_url`.
This class is a dependency-light seam for future background jobs and cache
management; it deliberately does not require the Earth Engine Python API.
"""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from luma.sources.catalog import get_source, resolve_remote_url, validate_year


@dataclass(frozen=True)
class MapBiomasProvider:
    """Resolve and optionally download a catalogued MapBiomas product."""

    source_key: str = "mapbiomas_brazil_col10_1"

    def __post_init__(self) -> None:
        source = get_source(self.source_key)
        if source.get("provider") != "mapbiomas":
            raise ValueError(f"Source '{self.source_key}' is not a MapBiomas product")

    @property
    def metadata(self) -> dict:
        """Return a defensive copy of the source metadata."""
        return copy.deepcopy(get_source(self.source_key))

    def url(self, year: int | None = None) -> str:
        """Return the public COG URL for *year* (latest year by default)."""
        source = self.metadata
        if year is None:
            years = source.get("years_range") or source.get("years") or []
            year = int(years[-1]) if years else None
        if year is not None:
            validate_year(self.source_key, int(year))
        return resolve_remote_url(self.source_key, 0.0, 0.0, year=year)

    def cache_key(self, year: int, bounds: tuple[float, float, float, float]) -> str:
        """Return a deterministic, source/version-aware cache filename."""
        validate_year(self.source_key, int(year))
        raw = f"{self.source_key}|{self.url(year)}|{tuple(float(v) for v in bounds)}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
        return f"mapbiomas_{digest}.tif"

    def download_window(
        self,
        year: int,
        bounds: tuple[float, float, float, float],
        output_path: Path | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> Path:
        """Download a clipped COG window through LUMA's existing cache layer."""
        from luma.core.downloader import download_cog_window

        if output_path is None:
            from luma.core.downloader import get_cache_dir

            output_path = get_cache_dir() / self.cache_key(year, bounds)
        return download_cog_window(
            self.url(year), bounds, output_path=output_path,
            progress_callback=progress_callback,
        )
