"""Regression tests for the scientific raster/statistics core.

These tests intentionally use tiny synthetic arrays so that each expected
value can be calculated by hand.  They are also used as the executable
contract for the temporal alignment and legend validation helpers.
"""

import numpy as np
import pytest
from rasterio.transform import Affine
from pyproj import CRS

from luma.core.raster import (
    RasterData,
    align_raster_to_reference,
    pixel_area_m2_from_transform,
)
from luma.core.stats import (
    compute_class_statistics,
    compute_landscape_metrics,
    compute_transition_matrix,
    validate_legend_classes,
)


def test_class_zero_is_counted_when_it_is_a_declared_class():
    data = np.array([[0, 1], [0, 1]], dtype=np.uint8)
    mask = np.ones_like(data, dtype=bool)
    legend = {
        0: {"name": "Water", "color": "#0000ff"},
        1: {"name": "Forest", "color": "#008000"},
    }

    stats = compute_class_statistics(data, mask, 100.0, legend)

    assert {s.class_id for s in stats} == {0, 1}
    water = next(s for s in stats if s.class_id == 0)
    assert water.pixel_count == 2
    assert water.area_m2 == 200.0
    assert water.percentage == pytest.approx(50.0)


def test_undeclared_zero_is_not_treated_as_nodata_class():
    data = np.array([[0, 1], [0, 1]], dtype=np.uint8)
    mask = np.ones_like(data, dtype=bool)
    stats = compute_class_statistics(data, mask, 100.0, {1: {"name": "Forest"}})

    assert [s.class_id for s in stats] == [1]
    assert stats[0].pixel_count == 2
    assert stats[0].percentage == pytest.approx(100.0)


def test_mesh_uses_connected_patch_areas_not_class_totals():
    # Class 1 has two one-pixel patches; class 2 is one four-pixel patch.
    data = np.array([[1, 2, 2], [2, 2, 2], [2, 2, 1]], dtype=np.uint8)
    mask = np.ones_like(data, dtype=bool)
    legend = {1: {"name": "A"}, 2: {"name": "B"}}
    stats = compute_class_statistics(data, mask, 1.0, legend)
    metrics = compute_landscape_metrics(stats, data, mask, 1.0)

    # Areas are 1, 1 and 7 m² => MESH = (1² + 1² + 7²) / 9 = 5.666... m².
    assert metrics.effective_mesh_size == pytest.approx(51 / 9, abs=0.01)


def test_temporal_alignment_reprojects_to_reference_grid():
    reference = RasterData(
        data=np.zeros((2, 2), dtype=np.uint8),
        transform=Affine.translation(0, 2) * Affine.scale(1, 1),
        crs=CRS.from_epsg(3857),
        nodata=None,
        pixel_area_m2=1.0,
    )
    # Same extent/resolution, shifted one pixel east.  After alignment only
    # the overlapping column is valid and values land on the reference grid.
    source = RasterData(
        data=np.array([[7, 8], [9, 10]], dtype=np.uint8),
        transform=Affine.translation(1, 2) * Affine.scale(1, 1),
        crs=CRS.from_epsg(3857),
        nodata=255,
        pixel_area_m2=1.0,
    )

    aligned = align_raster_to_reference(source, reference)

    assert aligned.data.shape == reference.data.shape
    assert aligned.transform == reference.transform
    assert aligned.crs == reference.crs
    assert aligned.valid_mask.tolist() == [[False, True], [False, True]]
    assert aligned.data.tolist() == [[255, 7], [255, 9]]


def test_transition_rejects_unaligned_shapes():
    with pytest.raises(ValueError, match="aligned"):
        compute_transition_matrix(
            np.zeros((2, 2), dtype=np.uint8),
            np.zeros((3, 3), dtype=np.uint8),
            np.ones((2, 2), dtype=bool),
            np.ones((3, 3), dtype=bool),
            1.0,
            {0: {"name": "Water"}},
        )


def test_pixel_area_uses_affine_determinant_for_projected_crs():
    transform = Affine(2, 0.5, 0, 0.25, -3, 0)
    # |a*e - b*d| = |2*(-3) - .5*.25| = 6.125 square metres.
    assert pixel_area_m2_from_transform(transform, CRS.from_epsg(3857)) == pytest.approx(6.125)


def test_legend_validation_reports_unknown_and_unused_ids():
    data = np.array([[1, 2], [2, 2]], dtype=np.uint8)
    mask = np.ones_like(data, dtype=bool)
    validation = validate_legend_classes(data, mask, {1: {"name": "Forest"}, 3: {"name": "Urban"}})

    assert validation.unknown_ids == (2,)
    assert validation.unused_ids == (3,)
    with pytest.raises(ValueError, match="2"):
        validate_legend_classes(
            data, mask, {1: {"name": "Forest"}}, strict=True
        )
