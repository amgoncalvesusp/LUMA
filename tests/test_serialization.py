from shapely.geometry import Polygon

from luma.core.aoi import AOI
from luma.output.serialization import serializable_parameters


def test_serializable_parameters_encode_aoi_without_shapely_objects():
    aoi = AOI(Polygon([(-47, -22), (-47, -21), (-46, -21), (-47, -22)]))
    params = serializable_parameters({"lat": -21.5, "lon": -46.5, "aoi": aoi})

    assert params["lat"] == -21.5
    assert params["aoi"]["geometry"]["type"] == "Polygon"
    assert params["aoi"]["crs"] == "EPSG:4326"
    assert params["aoi"]["area_m2"] > 0
