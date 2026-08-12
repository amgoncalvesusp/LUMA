from pathlib import Path

from luma.output.charts import (
    build_compare_gradient_figure,
    build_temporal_series_figure,
    save_figure,
)


class _Stats:
    def __init__(self, name, percentage):
        self.class_name = name
        self.percentage = percentage


class _Metrics:
    isa_index = 12.5
    shannon_diversity = 0.7
    simpson_diversity = 0.4
    largest_patch_index = 32.0
    total_patches = 4


def test_temporal_and_comparison_charts_can_be_exported(tmp_path: Path):
    temporal = [
        {"year": 2000, "class_stats": [_Stats("Forest", 60.0), _Stats("Urban", 40.0)]},
        {"year": 2020, "class_stats": [_Stats("Forest", 45.0), _Stats("Urban", 55.0)]},
    ]
    compare = [
        {"point_label": "A", "landscape_metrics": _Metrics()},
        {"point_label": "B", "landscape_metrics": _Metrics()},
    ]

    temporal_path = tmp_path / "temporal.png"
    compare_path = tmp_path / "compare.svg"
    save_figure(build_temporal_series_figure(temporal, "line"), temporal_path)
    save_figure(build_compare_gradient_figure(compare, "isa"), compare_path)

    assert temporal_path.stat().st_size > 1000
    assert compare_path.stat().st_size > 1000
