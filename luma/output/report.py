"""PDF report generator with bilingual support, all analysis types, and interpretation guide."""

from __future__ import annotations

import math
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, NextPageTemplate,
    Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

try:
    from matplotlib.figure import Figure as _MplFigure
    from matplotlib.backends.backend_agg import FigureCanvasAgg as _MplCanvas
    _MPL_OK = True
except Exception:
    _MPL_OK = False

import luma
from luma.core.stats import AnalysisResult
from luma.i18n.translator import t, set_language, get_language


# ── Shared styles ────────────────────────────────────────────────────────────

def _make_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "ReportTitle", parent=styles["Title"],
        fontSize=18, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "SectionHead", parent=styles["Heading2"],
        fontSize=13, spaceBefore=14, spaceAfter=6,
        textColor=colors.HexColor("#2c3e50"),
    ))
    styles.add(ParagraphStyle(
        "SubSection", parent=styles["Heading3"],
        fontSize=11, spaceBefore=10, spaceAfter=4,
        textColor=colors.HexColor("#34495e"),
    ))
    styles.add(ParagraphStyle(
        "BodyText2", parent=styles["BodyText"],
        fontSize=10, alignment=TA_JUSTIFY, leading=14,
    ))
    styles.add(ParagraphStyle(
        "MetricDetail", parent=styles["BodyText"],
        fontSize=9, alignment=TA_JUSTIFY, leading=13,
        spaceBefore=4, spaceAfter=6,
        leftIndent=6,
    ))
    styles.add(ParagraphStyle(
        "SmallGray", parent=styles["Normal"],
        fontSize=8, textColor=colors.gray,
    ))
    return styles


# ── Color constants ──────────────────────────────────────────────────────────

_HEADER_BG = colors.HexColor("#2c3e50")
_HEADER_FG = colors.white
_ROW_ALT = colors.HexColor("#f8f9fa")
_GRID_COLOR = colors.HexColor("#bdc3c7")
_PERSIST_BG = colors.HexColor("#d5f5e3")
_CHANGE_BG = colors.HexColor("#fadbd8")


# ── Public API ───────────────────────────────────────────────────────────────

def generate_pdf_report(
    path: str,
    result: AnalysisResult | None,
    params: dict,
    lang: str = "en",
    temporal_data: dict | None = None,
    temporal_years: tuple[int, int] = (0, 0),
    compare_data: list[dict] | None = None,
    temporal_series: list[dict] | None = None,
    compare_map_img: bytes | None = None,
) -> None:
    """Generate a complete PDF analysis report with all available analyses."""
    original_lang = get_language()
    set_language(lang)
    try:
        _build_pdf(path, result, params, temporal_data, temporal_years,
                   compare_data, temporal_series, compare_map_img)
    finally:
        set_language(original_lang)


# ── Main builder ─────────────────────────────────────────────────────────────

def _build_pdf(
    path: str,
    result: AnalysisResult | None,
    params: dict,
    temporal_data: dict | None,
    temporal_years: tuple[int, int],
    compare_data: list[dict] | None,
    temporal_series: list[dict] | None = None,
    compare_map_img: bytes | None = None,
) -> None:
    # Document with two page templates: portrait (default) and landscape
    # for wide tables (temporal transition matrix and compare panel).
    margin = 2 * cm
    portrait_size = A4
    landscape_size = landscape(A4)

    doc = BaseDocTemplate(
        path,
        pagesize=portrait_size,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin,
    )

    pw_p, ph_p = portrait_size
    pw_l, ph_l = landscape_size
    portrait_frame = Frame(
        margin, margin, pw_p - 2 * margin, ph_p - 2 * margin, id="portrait"
    )
    landscape_frame = Frame(
        margin, margin, pw_l - 2 * margin, ph_l - 2 * margin, id="landscape"
    )
    doc.addPageTemplates([
        PageTemplate(id="portrait", frames=[portrait_frame], pagesize=portrait_size),
        PageTemplate(id="landscape", frames=[landscape_frame], pagesize=landscape_size),
    ])

    styles = _make_styles()
    elements = []

    # ── Title ──
    _add_title(elements, styles)

    # ── Parameters ──
    if params:
        _add_parameters(elements, styles, result, params)

    # ── Single analysis (portrait) ──
    if result:
        _add_single_analysis(elements, styles, result)

    # ── Temporal analysis (landscape — wide transition matrix) ──
    if temporal_data:
        elements.append(NextPageTemplate("landscape"))
        elements.append(PageBreak())
        _add_temporal_analysis(elements, styles, temporal_data, temporal_years,
                               content_width=pw_l - 2 * margin)

    # ── Temporal time series ──
    if temporal_series:
        elements.append(NextPageTemplate("landscape"))
        elements.append(PageBreak())
        _add_temporal_series(elements, styles, temporal_series,
                             content_width=pw_l - 2 * margin)
        _add_series_chart(elements, styles, temporal_series,
                          content_width=pw_l - 2 * margin)

    # ── Compare points (landscape — many columns) ──
    if compare_data:
        elements.append(NextPageTemplate("landscape"))
        elements.append(PageBreak())
        _add_compare_analysis(elements, styles, compare_data,
                              content_width=pw_l - 2 * margin)
        _add_compare_gradient_chart(elements, styles, compare_data,
                                    content_width=pw_l - 2 * margin)

    # ── Compare map image ──
    if compare_map_img:
        elements.append(NextPageTemplate("portrait"))
        elements.append(PageBreak())
        _add_compare_map(elements, styles, compare_map_img)

    # ── Metric descriptions & formulas (back to portrait) ──
    elements.append(NextPageTemplate("portrait"))
    elements.append(PageBreak())
    _add_metric_details(elements, styles)

    # ── Citation ──
    _add_citation(elements, styles, result)

    doc.build(elements)


# ── Section builders ─────────────────────────────────────────────────────────

def _add_title(elements: list, styles) -> None:
    elements.append(Paragraph(t("report.title"), styles["ReportTitle"]))
    elements.append(Paragraph(
        t("report.generated_by", version=luma.__version__), styles["SmallGray"],
    ))
    elements.append(Paragraph(t("report.authors"), styles["SmallGray"]))
    elements.append(Paragraph(
        f"{t('report.date')}: {date.today().isoformat()}", styles["SmallGray"],
    ))
    elements.append(Spacer(1, 8 * mm))


def _add_parameters(elements: list, styles, result, params: dict) -> None:
    elements.append(Paragraph(t("report.parameters"), styles["SectionHead"]))
    lat = params.get("lat", 0)
    lon = params.get("lon", 0)
    radius = params.get("radius_m", 0)
    area_km2 = math.pi * (radius / 1000) ** 2

    data = [
        [t("report.center_coord"), f"{lat:.6f}, {lon:.6f}"],
        [t("report.buffer_radius"), f"{radius:,.0f} m"],
        [t("report.buffer_area"), f"{area_km2:.2f} km²"],
    ]
    if result:
        data.append([t("report.data_source"), result.source_name])
        data.append([t("report.accuracy"), result.source_accuracy])

    tbl = Table(data, colWidths=[5.5 * cm, 10 * cm])
    tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(tbl)
    elements.append(Spacer(1, 6 * mm))


def _add_single_analysis(elements: list, styles, result: AnalysisResult) -> None:
    # Quality warnings
    if result.quality_warnings:
        elements.append(Paragraph(t("report.quality_section"), styles["SectionHead"]))
        for w in result.quality_warnings:
            warn_text = t(f"warnings.{w}", n=result.total_valid_pixels)
            elements.append(Paragraph(f"⚠ {warn_text}", styles["BodyText2"]))
        elements.append(Spacer(1, 4 * mm))

    # Results table
    elements.append(Paragraph(t("report.results_section"), styles["SectionHead"]))
    header = [
        t("results.category"), t("results.pixels"),
        t("results.area_km2"), t("results.area_ha"), t("results.percentage"),
        t("results.num_patches"),
    ]
    table_data = [header]
    for cs in result.class_stats:
        table_data.append([
            cs.class_name,
            f"{cs.pixel_count:,}",
            f"{cs.area_m2 / 1e6:.4f}",
            f"{cs.area_m2 / 10_000:.2f}",
            f"{cs.percentage:.1f}%",
            str(cs.num_patches),
        ])

    col_widths = [5 * cm, 2 * cm, 2.2 * cm, 2.2 * cm, 2 * cm, 2 * cm]
    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), _HEADER_FG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, _GRID_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ROW_ALT]),
    ]))
    elements.append(tbl)
    elements.append(Spacer(1, 6 * mm))

    # Landscape metrics
    elements.append(Paragraph(t("report.metrics_section"), styles["SectionHead"]))
    m = result.landscape_metrics
    # ISA Walsh classification
    isa = m.isa_index
    if isa < 2:
        isa_cls = t("metrics.isa_ref")
    elif isa < 10:
        isa_cls = t("metrics.isa_sensitive")
    elif isa < 25:
        isa_cls = t("metrics.isa_impacted")
    else:
        isa_cls = t("metrics.isa_severe")

    metrics_data = [
        [t("metrics.shannon"), f"{m.shannon_diversity:.4f}"],
        [t("metrics.simpson"), f"{m.simpson_diversity:.4f}"],
        [t("metrics.dominance"), f"{m.dominance:.4f}"],
        [t("metrics.evenness"), f"{m.evenness:.4f}"],
        [t("metrics.total_patches"), f"{m.total_patches:,}"],
        [t("metrics.patch_density"), f"{m.patch_density:.2f}"],
        [t("metrics.lpi"), f"{m.largest_patch_index:.2f}%"],
        [t("metrics.edge_density"), f"{m.edge_density:.2f}"],
        [t("metrics.mesh_size"), f"{m.effective_mesh_size:,.2f}"],
        [t("metrics.aggregation_index"), f"{m.aggregation_index:.2f}%"],
        [t("metrics.contagion"), f"{m.contagion:.2f}%"],
        [t("metrics.mean_shape_index"), f"{m.mean_shape_index:.4f}"],
        [t("metrics.largest_patch_area"), f"{m.largest_patch_area_m2 / 10_000:,.2f}"],
        [t("metrics.smallest_patch_area"), f"{m.smallest_patch_area_m2 / 10_000:,.4f}"],
        [t("metrics.mean_patch_area"), f"{m.mean_patch_area_m2 / 10_000:,.2f}"],
        [t("metrics.isa_index"), f"{isa:.1f}%  ({isa_cls})"],
    ]
    tbl = Table(metrics_data, colWidths=[9 * cm, 5 * cm])
    tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#ddd")),
    ]))
    elements.append(tbl)
    elements.append(Spacer(1, 6 * mm))

    # Interpretation guide (brief)
    elements.append(Paragraph(t("report.interpretation"), styles["SectionHead"]))
    elements.append(Paragraph(t("report.interpretation_text"), styles["BodyText2"]))
    elements.append(Spacer(1, 4 * mm))


def _add_temporal_analysis(
    elements: list, styles,
    temporal_data: dict,
    temporal_years: tuple[int, int],
    content_width: float = 17 * cm,
) -> None:
    y1, y2 = temporal_years
    elements.append(Paragraph(t("report.temporal_section"), styles["SectionHead"]))
    elements.append(Paragraph(
        t("report.temporal_period", year1=y1, year2=y2), styles["BodyText2"],
    ))
    elements.append(Spacer(1, 3 * mm))

    matrix = temporal_data["matrix"]
    classes = temporal_data["classes"]
    legend = temporal_data["legend"]
    persistence = temporal_data["persistence"]
    net_change = temporal_data["net_change"]

    class_names = [legend.get(c, {}).get("name", f"Class {c}") for c in classes]

    # Transition matrix table
    elements.append(Paragraph(t("report.temporal_transition"), styles["SubSection"]))

    header = [t("report.temporal_from")] + class_names
    table_data = [header]
    for i, c1 in enumerate(classes):
        row = [class_names[i]]
        for c2 in classes:
            val = matrix[c1].get(c2, 0) / 1e6
            row.append(f"{val:.2f}")
        table_data.append(row)

    first_col = 4 * cm
    remaining = max(content_width - first_col, 1 * cm)
    col_w = min(2.4 * cm, remaining / max(len(classes), 1))
    col_widths = [first_col] + [col_w] * len(classes)

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Build style commands
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), _HEADER_FG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.4, _GRID_COLOR),
    ]
    # Highlight diagonal (persistence) and off-diagonal (change)
    for i in range(len(classes)):
        r = i + 1  # +1 for header row
        style_cmds.append(("BACKGROUND", (i + 1, r), (i + 1, r), _PERSIST_BG))
        for j in range(len(classes)):
            if i != j:
                val = matrix[classes[i]].get(classes[j], 0)
                if val > 0:
                    style_cmds.append(("BACKGROUND", (j + 1, r), (j + 1, r), _CHANGE_BG))

    tbl.setStyle(TableStyle(style_cmds))
    elements.append(tbl)
    elements.append(Spacer(1, 4 * mm))

    # Persistence
    elements.append(Paragraph(
        f"<b>{t('report.temporal_persistence')}:</b> {persistence:.1f}%",
        styles["BodyText2"],
    ))
    if "metrics_t1" in temporal_data and "metrics_t2" in temporal_data:
        isa1 = temporal_data["metrics_t1"].isa_index
        isa2 = temporal_data["metrics_t2"].isa_index
        delta = isa2 - isa1
        sign = "+" if delta >= 0 else ""
        elements.append(Paragraph(
            f"<b>{t('metrics.isa_index')}:</b> {isa1:.1f}% -> {isa2:.1f}% ({sign}{delta:.1f} p.p.)",
            styles["BodyText2"],
        ))
    elements.append(Spacer(1, 3 * mm))

    # Net change table — with % change column
    elements.append(Paragraph(t("report.temporal_net_change"), styles["SubSection"]))
    area_t1 = temporal_data.get("area_t1", {})
    nc_data = [[t("results.category"), "Δ km²", "Δ %"]]
    for c in classes:
        name = legend.get(c, {}).get("name", f"Class {c}")
        change_km2 = net_change.get(c, 0) / 1e6
        a_t1 = area_t1.get(c, 0) / 1e6
        sign = "+" if change_km2 > 0 else ""
        if a_t1 > 0:
            pct = change_km2 / a_t1 * 100
            pct_sign = "+" if pct > 0 else ""
            nc_data.append([name, f"{sign}{change_km2:.2f}", f"{pct_sign}{pct:.1f}%"])
        else:
            nc_data.append([name, f"{sign}{change_km2:.2f}", "—"])

    tbl = Table(nc_data, colWidths=[7 * cm, 3 * cm, 3 * cm], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), _HEADER_FG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#ddd")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ROW_ALT]),
    ]))
    elements.append(tbl)


def _add_compare_analysis(
    elements: list, styles, compare_data: list[dict],
    content_width: float = 17 * cm,
) -> None:
    elements.append(Paragraph(t("report.compare_section"), styles["SectionHead"]))

    # Collect all class names
    all_classes = []
    seen = set()
    for r in compare_data:
        for cs in r["class_stats"]:
            if cs.class_name not in seen:
                all_classes.append(cs.class_name)
                seen.add(cs.class_name)

    # Class distribution table — rows = points, cols = classes
    elements.append(Paragraph(t("report.compare_class_pct"), styles["SubSection"]))
    cls_first_col = 4 * cm
    cls_col_w = max(1.2 * cm, (content_width - cls_first_col) / max(len(all_classes), 1))
    cls_col_widths = [cls_first_col] + [cls_col_w] * len(all_classes)
    total_cls = sum(cls_col_widths)
    if total_cls > content_width:
        factor = content_width / total_cls
        cls_col_widths = [w * factor for w in cls_col_widths]

    header = [t("results.category")] + all_classes
    table_data = [header]
    for r in compare_data:
        row = [r["point_label"]]
        for cls_name in all_classes:
            pct = 0.0
            for cs in r["class_stats"]:
                if cs.class_name == cls_name:
                    pct = cs.percentage
                    break
            row.append(f"{pct:.1f}%")
        table_data.append(row)

    tbl = Table(table_data, colWidths=cls_col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), _HEADER_FG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.4, _GRID_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ROW_ALT]),
    ]))
    elements.append(tbl)
    elements.append(Spacer(1, 5 * mm))

    # Metrics comparison table — rows = points, cols = metrics
    elements.append(Paragraph(t("report.compare_metrics"), styles["SubSection"]))

    metric_defs = [
        ("compare.metric_shdi",          lambda m: f"{m.shannon_diversity:.3f}"),
        ("compare.metric_isa",           lambda m: f"{m.isa_index:.1f}%"),
        ("compare.metric_sidi",          lambda m: f"{m.simpson_diversity:.3f}"),
        ("compare.metric_evenness",      lambda m: f"{m.evenness:.3f}"),
        ("compare.metric_patches",       lambda m: f"{m.total_patches}"),
        ("compare.metric_patch_density", lambda m: f"{m.patch_density:.1f}"),
        ("compare.metric_lpi",           lambda m: f"{m.largest_patch_index:.1f}%"),
        ("compare.metric_aggregation",   lambda m: f"{m.aggregation_index:.1f}%"),
        ("compare.metric_contagion",     lambda m: f"{m.contagion:.1f}%"),
        ("compare.metric_shape",         lambda m: f"{m.mean_shape_index:.3f}"),
        ("compare.metric_area_max",      lambda m: f"{m.largest_patch_area_m2 / 10_000:,.2f}"),
        ("compare.metric_area_min",      lambda m: f"{m.smallest_patch_area_m2 / 10_000:,.2f}"),
        ("compare.metric_area_mean",     lambda m: f"{m.mean_patch_area_m2 / 10_000:,.2f}"),
    ]

    from reportlab.lib.styles import ParagraphStyle as _PS
    _hdr_style = _PS("_MetHdr", fontName="Helvetica-Bold", fontSize=7,
                     alignment=TA_CENTER, leading=8, wordWrap="CJK")

    met_first_col = 4 * cm
    met_col_w = max(1.2 * cm, (content_width - met_first_col) / len(metric_defs))
    met_col_widths = [met_first_col] + [met_col_w] * len(metric_defs)

    hdr_row = [Paragraph("", _hdr_style)] + [Paragraph(t(key), _hdr_style) for key, _ in metric_defs]
    table_data = [hdr_row]
    for r in compare_data:
        row = [r["point_label"]]
        for _, accessor in metric_defs:
            row.append(accessor(r["landscape_metrics"]))
        table_data.append(row)

    tbl = Table(table_data, colWidths=met_col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8e44ad")),
        ("TEXTCOLOR", (0, 0), (-1, 0), _HEADER_FG),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.4, _GRID_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ROW_ALT]),
    ]))
    elements.append(tbl)


def _render_mpl_image(fig, max_w_cm: float = 16):
    """Render a matplotlib Figure to a reportlab Image flowable."""
    from io import BytesIO
    from reportlab.platypus import Image as RLImage
    canvas = _MplCanvas(fig)
    buf = BytesIO()
    canvas.print_png(buf)
    buf.seek(0)
    img = RLImage(buf)
    iw, ih = img.imageWidth, img.imageHeight
    if iw and ih:
        scale = (max_w_cm * cm) / iw
        img.drawWidth = iw * scale
        img.drawHeight = ih * scale
    return img


def _add_compare_gradient_chart(elements, styles, compare_data, content_width):
    if not _MPL_OK or not compare_data:
        return
    labels = [r["point_label"] for r in compare_data]
    values = [r["landscape_metrics"].isa_index for r in compare_data]
    fig = _MplFigure(figsize=(6, 2.5), tight_layout=True)
    ax = fig.add_subplot(111)
    if values:
        vmin, vmax = min(values), max(values)
        span = (vmax - vmin) or 1.0
        cols = [(1 - (v - vmin)/span, 0.4, (v - vmin)/span) for v in values]
        ax.bar(range(len(labels)), values, color=cols, edgecolor="#222")
        ax.plot(range(len(labels)), values, color="#222", marker="o", linewidth=1)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("ISA (%)")
    ax.set_title("Gradient between points — ISA")
    elements.append(Spacer(1, 4 * mm))
    elements.append(_render_mpl_image(fig, max_w_cm=content_width / cm))


def _add_series_chart(elements, styles, temporal_series, content_width):
    if not _MPL_OK or not temporal_series:
        return
    years = [e["year"] for e in temporal_series]
    all_classes: list[str] = []
    seen = set()
    for entry in temporal_series:
        for cs in entry["class_stats"]:
            if cs.class_name not in seen:
                all_classes.append(cs.class_name)
                seen.add(cs.class_name)
    fig = _MplFigure(figsize=(6, 2.8), tight_layout=True)
    ax = fig.add_subplot(111)
    for cls in all_classes:
        ys = [
            next((cs.percentage for cs in e["class_stats"] if cs.class_name == cls), 0.0)
            for e in temporal_series
        ]
        ax.plot(years, ys, marker="o", label=cls)
    ax.set_ylabel("%")
    ax.legend(fontsize=6, loc="best", ncol=2)
    elements.append(Spacer(1, 4 * mm))
    elements.append(_render_mpl_image(fig, max_w_cm=content_width / cm))


def _add_temporal_series(
    elements: list, styles,
    temporal_series: list[dict],
    content_width: float = 17 * cm,
) -> None:
    """Longitudinal coverage table: rows = classes, cols = years."""
    if not temporal_series:
        return

    elements.append(Paragraph(t("report.temporal_series_section"), styles["SectionHead"]))
    elements.append(Spacer(1, 3 * mm))

    # Collect all class names preserving first-appearance order
    all_classes: list[str] = []
    seen: set[str] = set()
    for entry in temporal_series:
        for cs in entry["class_stats"]:
            if cs.class_name not in seen:
                all_classes.append(cs.class_name)
                seen.add(cs.class_name)

    years = [e["year"] for e in temporal_series]
    n_years = len(years)

    first_col = 4.5 * cm
    year_col_w = min(2.0 * cm, max(1.2 * cm, (content_width - first_col) / n_years))
    col_widths = [first_col] + [year_col_w] * n_years

    header = [t("results.category")] + [str(y) for y in years]
    table_data = [header]

    # Build per-entry lookup for speed
    lookup = [
        {cs.class_name: cs.percentage for cs in entry["class_stats"]}
        for entry in temporal_series
    ]

    for cls_name in all_classes:
        row = [cls_name]
        for ld in lookup:
            pct = ld.get(cls_name, 0.0)
            row.append(f"{pct:.1f}%")
        table_data.append(row)
    if all("landscape_metrics" in entry for entry in temporal_series):
        table_data.append([
            t("metrics.isa_index"),
            *[f"{entry['landscape_metrics'].isa_index:.1f}%" for entry in temporal_series],
        ])

    # Colour coding: compare each cell to previous year
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), _HEADER_FG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.4, _GRID_COLOR),
    ]
    for r_idx, cls_name in enumerate(all_classes):
        table_row = r_idx + 1
        prev_pct: float | None = None
        for c_idx, ld in enumerate(lookup):
            pct = ld.get(cls_name, 0.0)
            col = c_idx + 1
            if prev_pct is not None:
                if pct > prev_pct + 0.5:
                    style_cmds.append(("BACKGROUND", (col, table_row), (col, table_row), _PERSIST_BG))
                elif pct < prev_pct - 0.5:
                    style_cmds.append(("BACKGROUND", (col, table_row), (col, table_row), _CHANGE_BG))
            prev_pct = pct

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle(style_cmds))
    elements.append(tbl)
    elements.append(Spacer(1, 4 * mm))

    # Summary: first→last year delta
    first_map = lookup[0]
    last_map = lookup[-1]
    lines = [f"<b>{t('temporal.series_summary')} ({years[0]} → {years[-1]}):</b>"]
    for cls_name in all_classes:
        p0 = first_map.get(cls_name, 0.0)
        p1 = last_map.get(cls_name, 0.0)
        delta = p1 - p0
        sign = "+" if delta >= 0 else ""
        lines.append(f"  {cls_name}: {p0:.1f}% → {p1:.1f}%  ({sign}{delta:.1f} p.p.)")
    elements.append(Paragraph("<br/>".join(lines), styles["BodyText2"]))


def _add_compare_map(
    elements: list, styles,
    compare_map_img: bytes,
) -> None:
    """Embed the compare map PNG screenshot into the PDF."""
    from io import BytesIO
    from reportlab.platypus import Image as RLImage

    elements.append(Paragraph(t("report.compare_map_section"), styles["SectionHead"]))
    elements.append(Spacer(1, 4 * mm))

    img_buf = BytesIO(compare_map_img)
    img = RLImage(img_buf)

    max_w = 17 * cm
    max_h = 22 * cm
    iw = img.imageWidth
    ih = img.imageHeight
    if iw and ih:
        scale = min(max_w / iw, max_h / ih)
        img.drawWidth = iw * scale
        img.drawHeight = ih * scale
    else:
        img.drawWidth = max_w
        img.drawHeight = max_h

    elements.append(img)
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(t("report.compare_map_caption"), styles["SmallGray"]))


def _add_metric_details(elements: list, styles) -> None:
    """Add detailed metric descriptions with formulas and references."""
    elements.append(Paragraph(t("report.metric_detail_title"), styles["SectionHead"]))
    elements.append(Spacer(1, 3 * mm))

    detail_keys = [
        "report.metric_detail_shannon",
        "report.metric_detail_simpson",
        "report.metric_detail_dominance",
        "report.metric_detail_evenness",
        "report.metric_detail_patches",
        "report.metric_detail_patch_density",
        "report.metric_detail_lpi",
        "report.metric_detail_edge_density",
        "report.metric_detail_mesh",
        "report.metric_detail_aggregation",
        "report.metric_detail_contagion",
        "report.metric_detail_shape",
        "report.metric_detail_patch_area",
    ]

    for key in detail_keys:
        elements.append(Paragraph(t(key), styles["MetricDetail"]))


def _add_citation(elements: list, styles, result: AnalysisResult | None) -> None:
    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(
        width="100%", thickness=0.5, color=_GRID_COLOR,
    ))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(t("report.citation"), styles["SectionHead"]))
    source_name = result.source_name if result else "N/A"
    elements.append(Paragraph(
        t("report.citation_text", version=luma.__version__, source=source_name),
        styles["BodyText2"],
    ))
