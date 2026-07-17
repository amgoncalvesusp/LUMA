"""Serializable representations for exported analysis metadata."""

from __future__ import annotations

from collections.abc import Mapping


def serializable_parameters(parameters: Mapping[str, object]) -> dict[str, object]:
    """Return a JSON-safe copy of UI parameters, including an AOI summary."""
    result = dict(parameters)
    aoi = result.get("aoi")
    if aoi is None:
        return result
    result["aoi"] = {
        "geometry": aoi.to_geojson(),
        "crs": str(aoi.crs),
        "area_m2": aoi.area_m2,
        "name": aoi.name,
    }
    return result
