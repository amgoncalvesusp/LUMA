import pytest

from luma.sources.catalog import (
    get_source,
    list_sources,
    resolve_remote_url,
    validate_source_compatibility,
    validate_year,
)
from luma.sources.provider import MapBiomasProvider


def test_mapbiomas_10_1_catalog_metadata():
    source = get_source("mapbiomas_brazil_col10_1")
    assert source["provider"] == "mapbiomas"
    assert source["collection"] == "10.1"
    assert source["resolution_m"] == 30
    assert source["years_range"] == [1985, 2024]
    assert source["gee_asset"].endswith("mapbiomas_brazil_collection10_1_coverage_v1")
    assert source["asset_id"] == source["gee_asset"]
    assert "{year}" in source["url_template"]


def test_mapbiomas_10m_beta_catalog_metadata():
    source = get_source("mapbiomas_brazil_col3_10m")
    assert source["provider"] == "mapbiomas"
    assert source["collection"] == "3 beta"
    assert source["resolution_m"] == 10
    assert source["years_range"] == [2017, 2024]
    assert source["gee_asset"].endswith("mapbiomas_10m_collection3_integration_v1")


def test_mapbiomas_url_resolves_selected_year():
    url = resolve_remote_url("mapbiomas_brazil_col10_1", -21.79, -48.18, year=1985)
    assert url.endswith("brazil_coverage_1985.tif")


def test_year_validation_rejects_year_outside_product():
    with pytest.raises(ValueError, match="1984"):
        validate_year("mapbiomas_brazil_col10_1", 1984)
    assert validate_year("mapbiomas_brazil_col3_10m", 2024) is True


def test_temporal_comparison_requires_same_collection_and_resolution():
    assert validate_source_compatibility(
        "mapbiomas_brazil_col10_1", "mapbiomas_brazil_col10_1"
    ) is True
    with pytest.raises(ValueError, match="collection|resolution"):
        validate_source_compatibility(
            "mapbiomas_brazil_col10_1", "mapbiomas_brazil_col3_10m"
        )
    with pytest.raises(ValueError, match="collection|provider"):
        validate_source_compatibility(
            "mapbiomas_brazil_col10_1", "mapbiomas_brazil"
        )


def test_list_sources_exposes_catalog_metadata():
    sources = {source["key"]: source for source in list_sources()}
    assert sources["mapbiomas_brazil_col10_1"]["resolution"] == "30m"
    assert sources["mapbiomas_brazil_col3_10m"]["resolution"] == "10m"


def test_mapbiomas_provider_uses_catalog_and_cache_key():
    provider = MapBiomasProvider("mapbiomas_brazil_col3_10m")
    assert provider.url(2020).endswith("brazil_lulc_10m_2020.tif")
    assert provider.cache_key(2020, (-48.2, -21.8, -48.1, -21.7)).startswith("mapbiomas_")


def test_worldcover_url_uses_latitude_then_longitude_tile_grid():
    url = resolve_remote_url("esa_worldcover_2021", -23.55, -46.63)
    assert "S24W048" in url
