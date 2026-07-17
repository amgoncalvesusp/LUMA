"""Land cover statistics and landscape metrics."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage


@dataclass
class ClassStats:
    """Statistics for a single land-cover class."""
    class_id: int
    class_name: str
    pixel_count: int
    area_m2: float
    percentage: float
    num_patches: int = 0
    largest_patch_area_m2: float = 0.0
    color: str = "#888888"
    impervious: bool = False  # True when legend marks class as impervious surface


@dataclass
class LandscapeMetrics:
    """Landscape-level metrics for the entire buffer area."""
    shannon_diversity: float = 0.0
    simpson_diversity: float = 0.0
    dominance: float = 0.0
    evenness: float = 0.0
    total_patches: int = 0
    patch_density: float = 0.0
    largest_patch_index: float = 0.0
    edge_density: float = 0.0
    effective_mesh_size: float = 0.0
    aggregation_index: float = 0.0   # AI (%), McGarigal & Marks 1995
    contagion: float = 0.0           # CONTAG (%), O'Neill et al. 1988
    mean_shape_index: float = 0.0    # SHAPE_MN, McGarigal & Marks 1995
    largest_patch_area_m2: float = 0.0   # AREA_MX — largest single patch (m²)
    smallest_patch_area_m2: float = 0.0  # AREA_MN — smallest single patch (m²)
    mean_patch_area_m2: float = 0.0      # AREA_MEAN — mean patch size (m²)
    isa_index: float = 0.0               # Impervious Surface Area (Walsh 2005), %


@dataclass
class AnalysisResult:
    """Complete result of a land-cover analysis."""
    class_stats: list[ClassStats] = field(default_factory=list)
    landscape_metrics: LandscapeMetrics = field(default_factory=LandscapeMetrics)
    total_area_m2: float = 0.0
    total_valid_pixels: int = 0
    pixel_area_m2: float = 0.0
    quality_warnings: list[str] = field(default_factory=list)
    source_name: str = ""
    source_accuracy: str = ""
    # Optional clipped raster payload used only for thematic map rendering.
    # Keeping it optional preserves report/export compatibility for callers
    # that construct AnalysisResult from statistics alone.
    raster_data: object | None = field(default=None, repr=False)
    raster_valid_mask: object | None = field(default=None, repr=False)
    raster_transform: object | None = field(default=None, repr=False)
    raster_crs: object | None = field(default=None, repr=False)
    provenance: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class LegendValidation:
    """Relationship between IDs observed in a raster and a legend."""

    raster_ids: tuple[int, ...]
    legend_ids: tuple[int, ...]
    unknown_ids: tuple[int, ...]
    unused_ids: tuple[int, ...]

    @property
    def is_valid(self) -> bool:
        return not self.unknown_ids


def _validate_array_inputs(data: np.ndarray, valid_mask: np.ndarray) -> None:
    if data.ndim != 2:
        raise ValueError(f"Raster data must be 2-D, got shape {data.shape}")
    if valid_mask.shape != data.shape:
        raise ValueError(
            f"valid_mask shape {valid_mask.shape} does not match raster shape {data.shape}"
        )
    if valid_mask.dtype != bool:
        raise ValueError("valid_mask must have boolean dtype")


def validate_legend_classes(
    data: np.ndarray,
    valid_mask: np.ndarray,
    legend: dict[int, dict],
    *,
    strict: bool = False,
) -> LegendValidation:
    """Validate that every valid raster class has a legend entry."""
    _validate_array_inputs(data, valid_mask)
    raster_ids = tuple(int(v) for v in np.unique(data[valid_mask]))
    legend_ids = tuple(sorted(int(v) for v in legend))
    unknown = tuple(v for v in raster_ids if v not in legend)
    unused = tuple(v for v in legend_ids if v not in raster_ids)
    result = LegendValidation(raster_ids, legend_ids, unknown, unused)
    if strict and unknown:
        ids = ", ".join(str(v) for v in unknown)
        raise ValueError(f"Raster contains class IDs absent from legend: {ids}")
    return result


def compute_class_statistics(
    data: np.ndarray,
    valid_mask: np.ndarray,
    pixel_area_m2: float,
    legend: dict[int, dict],
) -> list[ClassStats]:
    """Compute per-class area and patch statistics.

    Parameters
    ----------
    data : np.ndarray
        2-D classified raster (integer class IDs).
    valid_mask : np.ndarray
        Boolean mask (True = valid pixel).
    pixel_area_m2 : float
        Area of a single pixel in m².
    legend : dict
        Mapping of class_id -> {"name": str, "color": str}.
    """
    _validate_array_inputs(data, valid_mask)
    effective_mask = valid_mask
    # Legacy rasters often have no explicit mask and use zero as NoData.  If
    # the chosen legend does not define class zero, exclude those cells from
    # both the denominator and patch calculations.
    if 0 not in legend:
        effective_mask = valid_mask & (data != 0)
    valid_data = data[effective_mask]
    total_valid = valid_data.size
    if total_valid == 0:
        return []

    unique_classes, counts = np.unique(valid_data, return_counts=True)
    results = []

    for cls_id, count in zip(unique_classes, counts):
        cls_id = int(cls_id)
        # Zero is a legitimate class in products such as Dynamic World.  It is
        # ignored only when the selected legend does not declare class zero.
        if cls_id == 0 and cls_id not in legend:
            continue
        cls_info = legend.get(cls_id, {"name": f"Class {cls_id}", "color": "#888888"})
        area = count * pixel_area_m2
        pct = (count / total_valid) * 100

        # Patch analysis for this class
        class_mask = (data == cls_id) & effective_mask
        labelled, num_patches = ndimage.label(class_mask)
        largest_patch = 0.0
        if num_patches > 0:
            patch_sizes = ndimage.sum(class_mask, labelled, range(1, num_patches + 1))
            largest_patch = float(np.max(patch_sizes)) * pixel_area_m2

        results.append(ClassStats(
            class_id=cls_id,
            class_name=cls_info["name"],
            pixel_count=int(count),
            area_m2=area,
            percentage=pct,
            num_patches=num_patches,
            largest_patch_area_m2=largest_patch,
            color=cls_info.get("color", "#888888"),
            impervious=bool(cls_info.get("impervious", False)),
        ))

    results.sort(key=lambda s: s.percentage, reverse=True)
    return results


def compute_landscape_metrics(
    class_stats: list[ClassStats],
    data: np.ndarray,
    valid_mask: np.ndarray,
    pixel_area_m2: float,
) -> LandscapeMetrics:
    """Compute landscape-level diversity and fragmentation metrics."""
    _validate_array_inputs(data, valid_mask)
    if not class_stats:
        return LandscapeMetrics()

    # Keep the metric mask consistent with class statistics: zero is omitted
    # when it is not represented in the selected legend.
    if not any(c.class_id == 0 for c in class_stats):
        valid_mask = valid_mask & (data != 0)

    total_area = sum(c.area_m2 for c in class_stats)
    if total_area == 0:
        return LandscapeMetrics()

    proportions = [c.area_m2 / total_area for c in class_stats]
    n_classes = len(class_stats)

    # Shannon Diversity Index: H = -Σ(pᵢ × ln(pᵢ))
    shannon = -sum(p * math.log(p) for p in proportions if p > 0)

    # Simpson Diversity Index: 1 - Σ(pᵢ²)
    simpson = 1.0 - sum(p ** 2 for p in proportions)

    # Maximum possible Shannon diversity
    h_max = math.log(n_classes) if n_classes > 1 else 1.0

    # Dominance: Hmax - H
    dominance = h_max - shannon

    # Evenness: H / Hmax
    evenness = shannon / h_max if h_max > 0 else 0.0

    # Total patches
    total_patches = sum(c.num_patches for c in class_stats)

    # Patch density (patches per km²)
    total_area_km2 = total_area / 1e6
    patch_density = total_patches / total_area_km2 if total_area_km2 > 0 else 0

    # Largest Patch Index (%)
    all_lpa = [c.largest_patch_area_m2 for c in class_stats]
    lpi = (max(all_lpa) / total_area * 100) if all_lpa else 0

    # Edge density (m/ha) — count transitions between different classes
    edge_pixels = _count_edge_pixels(data, valid_mask)
    pixel_side_m = math.sqrt(pixel_area_m2)
    total_edge_m = edge_pixels * pixel_side_m
    total_area_ha = total_area / 10_000
    edge_density = total_edge_m / total_area_ha if total_area_ha > 0 else 0

    # Effective Mesh Size: Σ(aᵢ²) / A_total
    # Effective mesh uses connected fragment areas, not aggregate class areas.
    all_patch_sizes_m2 = _all_patch_sizes_m2(
        data, valid_mask, pixel_area_m2, class_ids=(c.class_id for c in class_stats)
    )
    mesh_size = (
        sum(area ** 2 for area in all_patch_sizes_m2) / total_area
        if total_area > 0 else 0
    )

    # Aggregation Index (AI, %): He et al. 2000 / McGarigal & Marks 1995
    aggregation = _compute_aggregation_index(data, valid_mask, class_stats, pixel_area_m2)

    # Contagion (CONTAG, %): O'Neill et al. 1988
    contagion = _compute_contagion(data, valid_mask, n_classes)

    # Mean Shape Index (SHAPE_MN): mean of patch shape indices
    mean_shape = _compute_mean_shape_index(data, valid_mask, class_stats, pixel_area_m2)

    # Impervious Surface Area index (Walsh et al. 2005)
    isa_area = sum(c.area_m2 for c in class_stats if c.impervious)
    isa_index = round(isa_area / total_area * 100, 2) if total_area > 0 else 0.0

    # Patch area statistics — collect sizes across all classes
    all_patch_sizes_m2 = _all_patch_sizes_m2(
        data, valid_mask, pixel_area_m2, class_ids=(c.class_id for c in class_stats)
    )
    if all_patch_sizes_m2:
        largest_patch_area = max(all_patch_sizes_m2)
        smallest_patch_area = min(all_patch_sizes_m2)
        mean_patch_area = sum(all_patch_sizes_m2) / len(all_patch_sizes_m2)
    else:
        largest_patch_area = smallest_patch_area = mean_patch_area = 0.0

    return LandscapeMetrics(
        shannon_diversity=round(shannon, 4),
        simpson_diversity=round(simpson, 4),
        dominance=round(dominance, 4),
        evenness=round(evenness, 4),
        total_patches=total_patches,
        patch_density=round(patch_density, 2),
        largest_patch_index=round(lpi, 2),
        edge_density=round(edge_density, 2),
        effective_mesh_size=round(mesh_size, 2),
        aggregation_index=round(aggregation, 2),
        contagion=round(contagion, 2),
        mean_shape_index=round(mean_shape, 4),
        largest_patch_area_m2=round(largest_patch_area, 2),
        smallest_patch_area_m2=round(smallest_patch_area, 2),
        mean_patch_area_m2=round(mean_patch_area, 2),
        isa_index=isa_index,
    )


def _all_patch_sizes_m2(
    data: np.ndarray,
    valid_mask: np.ndarray,
    pixel_area_m2: float,
    class_ids=None,
) -> list[float]:
    """Return areas of all 4-connected valid patches in square metres."""
    sizes_m2: list[float] = []
    ids = np.unique(data[valid_mask]) if class_ids is None else class_ids
    for cls_id in ids:
        class_mask = (data == cls_id) & valid_mask
        labelled, n_patches = ndimage.label(class_mask)
        if n_patches == 0:
            continue
        sizes = ndimage.sum(class_mask, labelled, range(1, n_patches + 1))
        sizes_m2.extend(float(size) * pixel_area_m2 for size in sizes)
    return sizes_m2


def _count_edge_pixels(data: np.ndarray, valid_mask: np.ndarray) -> int:
    """Count the number of pixel-side transitions between different classes."""
    edges = 0
    # Horizontal transitions
    h_diff = (data[:, :-1] != data[:, 1:]) & valid_mask[:, :-1] & valid_mask[:, 1:]
    edges += int(h_diff.sum())
    # Vertical transitions
    v_diff = (data[:-1, :] != data[1:, :]) & valid_mask[:-1, :] & valid_mask[1:, :]
    edges += int(v_diff.sum())
    return edges


def _compute_aggregation_index(
    data: np.ndarray,
    valid_mask: np.ndarray,
    class_stats: list[ClassStats],
    pixel_area_m2: float,
) -> float:
    """Aggregation Index (AI, %) — He, Dezonia & Mladenoff (2000).

    AI = 100 × Σ (g_ii / g_ii_max) × p_i

    where g_ii = number of like-adjacencies of class i (shared sides between
    same-class pixels), and g_ii_max = maximum possible like-adjacencies for
    class i given its pixel count.
    """
    if not class_stats:
        return 0.0

    total_ai = 0.0
    total_area = sum(c.area_m2 for c in class_stats)
    if total_area == 0:
        return 0.0

    for cs in class_stats:
        class_mask = (data == cs.class_id) & valid_mask
        n_pixels = int(class_mask.sum())
        if n_pixels == 0:
            continue

        # Count like-adjacencies (shared sides between same-class pixels)
        h_like = (class_mask[:, :-1] & class_mask[:, 1:]).sum()
        v_like = (class_mask[:-1, :] & class_mask[1:, :]).sum()
        g_ii = int(h_like + v_like)

        # Maximum possible like-adjacencies for a compact square arrangement
        # (He, Dezonia & Mladenoff 2000):
        #   m = floor(sqrt(n))
        #   if n == m²             : g_ii_max = 2m(m-1)
        #   if m² < n ≤ m² + m     : g_ii_max = 2m(m-1) + 2(n-m²) - 1
        #   otherwise              : g_ii_max = 2m(m-1) + 2(n-m²) - 2
        m = int(math.floor(math.sqrt(n_pixels)))
        m2 = m * m
        if n_pixels == m2:
            g_ii_max = 2 * m * (m - 1)
        elif n_pixels <= m2 + m:
            g_ii_max = 2 * m * (m - 1) + 2 * (n_pixels - m2) - 1
        else:
            g_ii_max = 2 * m * (m - 1) + 2 * (n_pixels - m2) - 2

        if g_ii_max <= 0:
            continue

        p_i = cs.area_m2 / total_area
        total_ai += (g_ii / g_ii_max) * p_i

    return 100.0 * total_ai


def _compute_contagion(
    data: np.ndarray,
    valid_mask: np.ndarray,
    n_classes: int,
) -> float:
    """Contagion Index (CONTAG, %) — O'Neill et al. (1988), Li & Reynolds (1993).

    CONTAG = 100 × (1 + Σ_{i,j} P_ij · ln(P_ij) / (2·ln(n)))

    where P_ij is the probability of a randomly chosen adjacent pair being of
    classes i and j. Includes both same-class and different-class adjacencies.
    """
    if n_classes <= 1:
        return 100.0  # Single class = maximum contagion

    # Build adjacency count dict: {(i, j): count} using 4-neighbor
    classes_present = np.unique(data[valid_mask])
    if classes_present.size <= 1:
        return 100.0

    # Count adjacencies as unordered pairs (i, j) with i<=j
    adj: dict[tuple[int, int], int] = {}

    # Horizontal pairs
    left = data[:, :-1]
    right = data[:, 1:]
    vm_l = valid_mask[:, :-1]
    vm_r = valid_mask[:, 1:]
    valid_h = vm_l & vm_r
    h_left = left[valid_h]
    h_right = right[valid_h]
    # Vertical pairs
    top = data[:-1, :]
    bottom = data[1:, :]
    vm_t = valid_mask[:-1, :]
    vm_b = valid_mask[1:, :]
    valid_v = vm_t & vm_b
    v_top = top[valid_v]
    v_bottom = bottom[valid_v]

    pairs_a = np.concatenate([h_left, v_top])
    pairs_b = np.concatenate([h_right, v_bottom])
    total_adj = pairs_a.size
    if total_adj == 0:
        return 0.0

    # Use np.unique to count unique pairs (ordered, then normalize)
    keys = pairs_a.astype(np.int64) * 10_000 + pairs_b.astype(np.int64)
    uniq, counts = np.unique(keys, return_counts=True)

    # Compute P_ij as fraction of all adjacencies
    contag_sum = 0.0
    for k, c in zip(uniq, counts):
        p_ij = c / total_adj
        if p_ij > 0:
            contag_sum += p_ij * math.log(p_ij)

    max_entropy = 2.0 * math.log(n_classes)
    if max_entropy == 0:
        return 0.0
    contag = 1.0 + (contag_sum / max_entropy)
    return 100.0 * max(0.0, min(1.0, contag))


def _compute_mean_shape_index(
    data: np.ndarray,
    valid_mask: np.ndarray,
    class_stats: list[ClassStats],
    pixel_area_m2: float,
) -> float:
    """Mean Shape Index (SHAPE_MN) — McGarigal & Marks (1995).

    SHAPE = 0.25 × perimeter / √area  (for raster, with perimeter in pixel-sides
    and area in pixels). SHAPE_MN is the mean over all patches.

    SHAPE = 1.0 for a perfect square patch; higher values indicate more complex
    or irregular patch shapes.
    """
    pixel_side = math.sqrt(pixel_area_m2)
    shape_values: list[float] = []

    for cs in class_stats:
        class_mask = (data == cs.class_id) & valid_mask
        labelled, num_patches = ndimage.label(class_mask)
        if num_patches == 0:
            continue

        for patch_id in range(1, num_patches + 1):
            patch_mask = labelled == patch_id
            n_pixels = int(patch_mask.sum())
            if n_pixels == 0:
                continue

            area = n_pixels * pixel_area_m2

            # Perimeter: count pixel-sides exposed to a different class or outside
            # Pad with False so boundary pixels count their exterior sides
            padded = np.pad(patch_mask, 1, constant_values=False)
            # Shared edges with neighbor pixels of SAME patch
            inner_h = (padded[1:-1, 1:-1] & padded[1:-1, 2:]).sum()
            inner_v = (padded[1:-1, 1:-1] & padded[2:, 1:-1]).sum()
            # Each pixel has 4 sides; subtract shared sides ×2
            perimeter_sides = 4 * n_pixels - 2 * int(inner_h + inner_v)
            perimeter = perimeter_sides * pixel_side

            if area > 0:
                shape = 0.25 * perimeter / math.sqrt(area)
                shape_values.append(shape)

    if not shape_values:
        return 0.0
    return float(np.mean(shape_values))


def compute_transition_matrix(
    data_t1: np.ndarray,
    data_t2: np.ndarray,
    valid_mask_t1: np.ndarray,
    valid_mask_t2: np.ndarray,
    pixel_area_m2: float,
    legend: dict[int, dict],
    *,
    strict_legend: bool = False,
) -> dict:
    """Compute a land-cover transition matrix between two time periods.

    Returns
    -------
    dict with keys:
        "matrix" : dict[int, dict[int, float]]  — area in m² from class i to class j
        "classes" : list[int]  — sorted list of all class IDs present
        "persistence" : float  — % of area unchanged
        "net_change" : dict[int, float]  — net area change per class in m²
    """
    _validate_array_inputs(data_t1, valid_mask_t1)
    _validate_array_inputs(data_t2, valid_mask_t2)
    if data_t1.shape != data_t2.shape:
        raise ValueError(
            "Temporal rasters must be aligned to the same shape before transition analysis"
        )
    combined_mask = valid_mask_t1 & valid_mask_t2
    d1 = data_t1[combined_mask]
    d2 = data_t2[combined_mask]
    if 0 not in legend:
        non_nodata = (d1 != 0) & (d2 != 0)
        d1 = d1[non_nodata]
        d2 = d2[non_nodata]

    all_classes = sorted(set(np.unique(d1).tolist()) | set(np.unique(d2).tolist()))
    if 0 not in legend:
        all_classes = [c for c in all_classes if c != 0]
    unknown = [int(c) for c in all_classes if int(c) not in legend]
    if strict_legend and unknown:
        ids = ", ".join(str(v) for v in unknown)
        raise ValueError(f"Raster contains class IDs absent from legend: {ids}")

    matrix: dict[int, dict[int, float]] = {}
    for c1 in all_classes:
        matrix[c1] = {}
        for c2 in all_classes:
            count = int(np.sum((d1 == c1) & (d2 == c2)))
            matrix[c1][c2] = count * pixel_area_m2

    total = d1.size * pixel_area_m2
    persistence_area = sum(matrix[c].get(c, 0) for c in all_classes)
    persistence_pct = (persistence_area / total * 100) if total > 0 else 0

    net_change = {}
    for c in all_classes:
        gained = sum(matrix[c2].get(c, 0) for c2 in all_classes if c2 != c)
        lost = sum(matrix[c].get(c2, 0) for c2 in all_classes if c2 != c)
        net_change[c] = gained - lost

    # Per-class area at each time point (sum of rows / columns in the matrix)
    area_t1 = {c: sum(matrix[c].values()) for c in all_classes}
    area_t2 = {c: sum(matrix[c2].get(c, 0) for c2 in all_classes) for c in all_classes}

    return {
        "matrix": matrix,
        "classes": all_classes,
        "persistence": round(persistence_pct, 2),
        "net_change": net_change,
        "area_t1": area_t1,
        "area_t2": area_t2,
        "legend": legend,
    }


def generate_quality_warnings(
    total_pixels: int, pixel_area_m2: float, radius_m: float
) -> list[str]:
    """Generate data-quality warnings for the analysis."""
    warnings = []
    if total_pixels < 30:
        warnings.append("CRITICAL_FEW_PIXELS")
    elif total_pixels < 100:
        warnings.append("LOW_PIXEL_COUNT")

    expected_area = math.pi * radius_m ** 2
    actual_area = total_pixels * pixel_area_m2
    coverage = actual_area / expected_area if expected_area > 0 else 0
    if coverage < 0.5:
        warnings.append("LOW_COVERAGE")

    pixel_side = math.sqrt(pixel_area_m2)
    if pixel_side > radius_m * 0.5:
        warnings.append("RESOLUTION_TOO_COARSE")

    return warnings


def compute_fao_deforestation_rate(
    area_t1: float, area_t2: float, year_t1: int, year_t2: int
) -> float:
    """Compute FAO annual deforestation rate: r = 1 - (A2/A1)^(1/(t2-t1))."""
    if area_t1 <= 0 or year_t1 == year_t2:
        return 0.0
    ratio = area_t2 / area_t1
    if ratio <= 0:
        return 1.0
    years = year_t2 - year_t1
    return 1.0 - ratio ** (1.0 / years)
