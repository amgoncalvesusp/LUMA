from luma.core.project import build_project, load_project, save_project
from luma.core.aoi import AOI
from shapely.geometry import Polygon


def test_project_round_trip_preserves_reproducibility_metadata(tmp_path):
    aoi = AOI(Polygon([(-47, -22), (-47, -21), (-46, -21), (-47, -22)]))
    payload = build_project(
        {"lat": -21.5, "lon": -46.5, "radius_m": 5000, "aoi": aoi},
        source_key="mapbiomas_brazil_col10_1",
        source_year=2020,
        legend_key="mapbiomas_col10",
    )
    path = tmp_path / "sample.luma.json"
    save_project(path, payload)
    loaded = load_project(path)

    assert loaded["format"] == "luma-project"
    assert loaded["version"] == 1
    assert loaded["source"]["year"] == 2020
    assert loaded["parameters"]["aoi"]["geometry"]["type"] == "Polygon"
