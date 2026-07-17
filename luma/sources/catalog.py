"""Data source catalog — maps source names to legends and remote URLs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from luma.i18n.translator import get_language

LEGENDS_DIR = Path(__file__).parent.parent / "legends"
SOURCES_FILE = Path(__file__).parent / "sources.yaml"


def load_legend(legend_name: str) -> dict[str, Any]:
    """Load a legend YAML file by name (without extension)."""
    path = LEGENDS_DIR / f"{legend_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Legend file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_legend_classes(legend_name: str) -> dict[int, dict]:
    """Load the classes dict from a legend, keyed by integer class ID.

    When the current language is pt_BR and a class has a 'name_pt' field,
    that field is used as the class name.
    """
    legend = load_legend(legend_name)
    use_pt = get_language() == "pt_BR"
    result = {}
    for k, v in legend.get("classes", {}).items():
        cls = dict(v)
        if use_pt and "name_pt" in cls:
            cls["name"] = cls["name_pt"]
        result[int(k)] = cls
    return result


def load_sources() -> dict[str, Any]:
    """Load the sources catalog."""
    if not SOURCES_FILE.exists():
        return {}
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_source(source_name: str) -> dict:
    """Get a specific data source configuration."""
    sources = load_sources()
    all_sources = sources.get("sources", {})
    if source_name not in all_sources:
        raise KeyError(
            f"Source '{source_name}' not found. "
            f"Available: {list(all_sources.keys())}"
        )
    return all_sources[source_name]


def list_sources() -> list[dict]:
    """List all available data sources with metadata."""
    sources = load_sources()
    result = []
    for key, src in sources.get("sources", {}).items():
        legend_info = load_legend(src["legend"])
        result.append({
            "key": key,
            "name": src.get("display_name", key),
            "legend": src["legend"],
            # Source-level values take precedence over legend defaults.  This
            # matters for MapBiomas 10 m, which shares class IDs with the
            # 30 m legend but has a different spatial resolution and series.
            "resolution": src.get("resolution", legend_info.get("resolution", "Unknown")),
            "resolution_m": src.get("resolution_m"),
            "coverage": src.get("coverage", legend_info.get("coverage", "Unknown")),
            "accuracy": src.get("reported_accuracy", legend_info.get("reported_accuracy", "Unknown")),
            "temporal_range": src.get("temporal_range", legend_info.get("temporal_range", "Unknown")),
            "url_template": src.get("url_template", ""),
            "download_url": src.get("download_url", ""),
            "download_instructions": src.get("download_instructions", ""),
            "type": src.get("type", "local"),
            "provider": src.get("provider"),
            "collection": src.get("collection"),
            "gee_asset": src.get("gee_asset"),
            "asset_id": src.get("asset_id", src.get("gee_asset")),
            "years_range": src.get("years_range"),
            "compatibility": src.get("compatibility", {}),
        })
    return result


def resolve_remote_url(
    source_key: str, lat: float, lon: float, year: int | None = None
) -> str:
    """Resolve a remote COG URL for the given coordinates.

    Handles tile grid calculation for ESA WorldCover-style URLs.
    """
    src = get_source(source_key)
    url_template = src.get("url_template", "")
    if not url_template:
        raise ValueError(f"Source '{source_key}' has no url_template")

    tile_grid_name = src.get("tile_grid")
    if tile_grid_name == "esa_worldcover":
        import math
        step = 3
        # Tile named by its SW corner: floor to nearest grid step
        lat_sw = math.floor(lat / step) * step
        lon_sw = math.floor(lon / step) * step

        lat_h = "N" if lat_sw >= 0 else "S"
        lon_h = "E" if lon_sw >= 0 else "W"
        lat_tile = f"{lat_h}{abs(lat_sw):02d}"
        lon_tile = f"{lon_h}{abs(lon_sw):03d}"

        return url_template.format(lat_tile=lat_tile, lon_tile=lon_tile)

    # Fallback: try simple substitution
    if year is None:
        years = src.get("years_range") or src.get("years") or []
        year = years[-1] if years else None

    return url_template.format(lat=lat, lon=lon, year=year)


def validate_year(source_key: str, year: int) -> bool:
    """Validate that *year* belongs to a source's declared temporal range.

    A ``ValueError`` is raised instead of silently falling back to a nearby
    year, because temporal analyses must remain reproducible.
    """
    src = get_source(source_key)
    years = src.get("years_range")
    if years:
        first, last = int(years[0]), int(years[1])
        if not first <= int(year) <= last:
            raise ValueError(
                f"Year {year} is outside the supported range {first}-{last} "
                f"for source '{source_key}'."
            )
    elif src.get("years") and int(year) not in {int(item) for item in src["years"]}:
        raise ValueError(
            f"Year {year} is not available for source '{source_key}'."
        )
    return True


def validate_source_compatibility(source_a: str, source_b: str) -> bool:
    """Ensure two sources can be compared in a temporal analysis.

    Temporal comparisons are only valid for the same provider, product,
    collection and pixel size.  Local/legacy sources without these metadata
    remain compatible with themselves for backwards compatibility.
    """
    first, second = get_source(source_a), get_source(source_b)
    fields = ("provider", "product", "collection", "resolution_m")
    mismatches = [
        field for field in fields
        if (first.get(field) is not None or second.get(field) is not None)
        and first.get(field) != second.get(field)
    ]
    if mismatches:
        raise ValueError(
            "Sources are not temporally compatible; differing metadata: "
            + ", ".join(mismatches)
        )
    return True


def list_legends() -> list[dict]:
    """List all available legends."""
    result = []
    for path in sorted(LEGENDS_DIR.glob("*.yaml")):
        legend = load_legend(path.stem)
        result.append({
            "key": path.stem,
            "name": legend.get("name", path.stem),
            "resolution": legend.get("resolution", "Unknown"),
            "coverage": legend.get("coverage", "Unknown"),
            "accuracy": legend.get("reported_accuracy", "Unknown"),
            "num_classes": len(legend.get("classes", {})),
        })
    return result
