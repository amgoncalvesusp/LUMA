"""CONTAG examples calculated from the FRAGSTATS double-count definition.

https://fragstats.org/index.php/fragstats-metrics/patch-based-metrics/aggregation-metrics/l1-contagion-index
"""

import math

import numpy as np
import pytest

from luma.core.stats import (
    _compute_contagion,
    compute_class_statistics,
    compute_landscape_metrics,
)


def test_contagion_uses_class_area_and_conditional_double_count_adjacency():
    # p=(3/4,1/4), g=((4,2),(2,0)); joint terms=(1/2,1/4,1/4).
    data = np.array([[1, 1], [1, 2]])
    mask = np.ones_like(data, dtype=bool)
    assert _compute_contagion(data, mask, 2) == pytest.approx(25.0)
    classes = compute_class_statistics(data, mask, 1, {1: {"name": "A"}, 2: {"name": "B"}})
    assert compute_landscape_metrics(classes, data, mask, 1).contagion == 25.0


@pytest.mark.parametrize("rotation", range(4))
@pytest.mark.parametrize("reflect", [False, True])
def test_contagion_is_invariant_to_map_rotation_and_reflection(rotation, reflect):
    data = np.array([[1, 2, 2], [1, 1, 2], [1, 2, 1]])
    expected = _compute_contagion(data, np.ones_like(data, dtype=bool), 2)
    transformed = np.rot90(np.fliplr(data) if reflect else data, rotation)
    assert _compute_contagion(transformed, np.ones_like(data, dtype=bool), 2) == pytest.approx(expected)


def test_contagion_ignores_background_and_preserves_large_class_ids():
    data = np.array([[1, 1, 20001], [99999, 99999, 99999]])
    mask = np.array([[True, True, True], [False, False, False]])
    probabilities = [4 / 9, 2 / 9, 1 / 3]
    expected = 100 * (1 + sum(p * math.log(p) for p in probabilities) / (2 * math.log(2)))
    assert _compute_contagion(data, mask, 2) == pytest.approx(expected)


@pytest.mark.parametrize("data,mask,n_classes", [
    ([[1, 1]], [[True, True]], 1),
    ([[1, 99, 2]], [[True, False, True]], 2),
    ([[1]], [[False]], 0),
])
def test_undefined_contagion_is_missing(data, mask, n_classes):
    assert _compute_contagion(np.array(data), np.array(mask), n_classes) is None
