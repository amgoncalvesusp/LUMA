"""Reusable Matplotlib figures for on-screen and file chart exports."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


def _class_names(series: list[dict]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for entry in series:
        for stats in entry.get("class_stats", []):
            if stats.class_name not in seen:
                names.append(stats.class_name)
                seen.add(stats.class_name)
    return names


def _percentage(entry: dict, class_name: str) -> float:
    return next(
        (float(stats.percentage) for stats in entry.get("class_stats", []) if stats.class_name == class_name),
        0.0,
    )


def build_temporal_series_figure(series: list[dict], chart_type: str = "bar") -> Figure:
    """Create a class-percentage chart for a temporal series."""
    if not series:
        raise ValueError("Temporal series is empty")
    if chart_type not in {"bar", "line"}:
        raise ValueError("chart_type must be 'bar' or 'line'")
    years = [entry["year"] for entry in series]
    names = _class_names(series)
    figure = Figure(figsize=(7, 4), dpi=120, tight_layout=True)
    canvas = FigureCanvasAgg(figure)
    axis = figure.add_subplot(111)
    values = [[_percentage(entry, name) for entry in series] for name in names]
    if chart_type == "line":
        for name, percentages in zip(names, values):
            axis.plot(years, percentages, marker="o", label=name)
    else:
        width = 0.8 / max(len(names), 1)
        x = np.arange(len(years))
        for index, (name, percentages) in enumerate(zip(names, values)):
            axis.bar(x + index * width - 0.4 + width / 2, percentages, width, label=name)
        axis.set_xticks(x)
        axis.set_xticklabels([str(year) for year in years])
    axis.set_xlabel("Year")
    axis.set_ylabel("Coverage (%)")
    axis.set_ylim(0, 100)
    axis.grid(axis="y", alpha=0.25)
    if names:
        axis.legend(fontsize=8, loc="best", ncol=2)
    canvas.draw()
    return figure


_COMPARE_ACCESSORS = {
    "isa": ("ISA (%)", lambda metrics: metrics.isa_index),
    "shdi": ("SHDI", lambda metrics: metrics.shannon_diversity),
    "sidi": ("SIDI", lambda metrics: metrics.simpson_diversity),
    "lpi": ("LPI (%)", lambda metrics: metrics.largest_patch_index),
    "patches": ("Patches", lambda metrics: metrics.total_patches),
}


def build_compare_gradient_figure(results: list[dict], metric: str = "isa") -> Figure:
    """Create the comparison gradient chart for the selected metric."""
    if not results:
        raise ValueError("Comparison results are empty")
    if metric not in _COMPARE_ACCESSORS:
        raise ValueError(f"Unknown comparison metric: {metric}")
    metric_label, accessor = _COMPARE_ACCESSORS[metric]
    labels = [str(result.get("point_label", "")) for result in results]
    values = [float(accessor(result["landscape_metrics"])) for result in results]
    figure = Figure(figsize=(7, 4), dpi=120, tight_layout=True)
    canvas = FigureCanvasAgg(figure)
    axis = figure.add_subplot(111)
    x = np.arange(len(labels))
    minimum, maximum = min(values), max(values)
    span = maximum - minimum or 1.0
    colors = [(1 - (value - minimum) / span, 0.4, (value - minimum) / span) for value in values]
    axis.bar(x, values, color=colors, edgecolor="#222")
    axis.plot(x, values, color="#222", marker="o", linewidth=1)
    axis.set_xticks(x)
    axis.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    axis.set_ylabel(metric_label)
    axis.grid(axis="y", alpha=0.25)
    canvas.draw()
    return figure


def save_figure(figure: Figure, path: str | Path) -> Path:
    """Save a figure using the extension selected by the user."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180, bbox_inches="tight")
    return output
