from luma.core.stats import compute_class_statistics, compute_landscape_metrics
from luma.output.report import generate_pdf_report
import numpy as np


def test_pdf_report_contains_polygon_comparison_data(tmp_path):
    data = np.array([[1, 1], [2, 2]], dtype=np.uint8)
    mask = np.ones_like(data, dtype=bool)
    legend = {1: {"name": "Floresta", "color": "#008000"}, 2: {"name": "Agricultura", "color": "#ffff00"}}
    stats = compute_class_statistics(data, mask, 100.0, legend)
    metrics = compute_landscape_metrics(stats, data, mask, 100.0)
    path = tmp_path / "comparison.pdf"

    generate_pdf_report(
        str(path), None, {}, lang="pt_BR",
        compare_data=[{
            "point_label": "Área 1",
            "geometry_area_m2": 12_345.0,
            "class_stats": stats,
            "landscape_metrics": metrics,
        }],
    )

    assert path.exists()
    assert path.stat().st_size > 1000
