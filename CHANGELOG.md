# Changelog

All notable changes to LUMA are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/) and the project adheres to
[Semantic Versioning](https://semver.org/).

## [1.2.0] - 2026-07-16

### Added
- Responsive compact mode for notebook-sized and high-DPI screens.
- Explicit navigation between the input panel and results on compact layouts.
- Contextual empty-state guidance for results and larger accessible help controls.

### Changed
- Reorganized analysis, temporal, point-comparison and polygon-comparison layouts.
- Kept the primary analysis action visible in standard layouts.
- Synchronized research objectives with the corresponding analysis tabs.
- Completed Portuguese/English refresh for polygon drawing and comparison results.

## [1.1.0] - 2026-05-28

### Added
- **Temporal analysis**
  - Chart-type selector (bar / line) for multi-year series.
  - Toggle to show/hide the multi-year maps grid.
  - Map grid caps at 10 panels — when more years are selected, only the
    oldest and the most recent are rendered.
- **Single analysis**
  - Right-side results panel is now wrapped in a scrollable area so all
    metrics remain reachable on small screens.
  - Landscape-metrics panel uses a compact 10 px layout.
- **Results table**
  - Inline metric legend rendered below every results table (i18n).
- **Coordinate inputs**
  - Paste handling for lat / lon fields: accepts `"lat, lon"` pairs,
    `-23,55` (comma decimal), degree symbols and N/S/E/W markers.
  - Pasting a pair into either field fills both lat and lon.
- **Multi-point comparison**
  - Preview panel listing selected points before processing.
  - Gradient chart (matplotlib) with metric selector
    (ISA, SHDI, SIDI, LPI, Patches).
  - "Open map" button — jumps to the Compare Map tab with every point,
    its buffer and label.
  - Bulk download bundle: `.kml`, `.kmz`, `.shp` (points + buffers, WGS84
    PRJ) and a `.tif` of the map. QGIS / Google Earth-ready.
  - "Export map as TIFF" — TIFF screenshot with a class-color legend
    composited below the map (uses Pillow).
- **Maps**
  - EPSG (UTM) label overlay on every map (single, buffer, compare).
  - Compare-points map: optional value gradient (color ramp + min/max
    legend) driven by the chosen metric.
- **PDF report**
  - Embedded matplotlib charts for temporal series and the compare
    gradient.
- **Panels**
  - All `QSplitter` handles widened and non-collapsible so panels can be
    resized via drag.
- **i18n**
  - New `ui`, `legend_table`, and `compare_extra` sections in both
    `pt_BR.yaml` and `en.yaml`.

### Changed
- Bumped to `1.1.0` (`pyproject.toml`, `luma/__init__.py`, `luma/main.py`).
- Added runtime dependencies: `pyshp>=2.3`, `simplekml>=1.3`.

### Notes
- No breaking changes. Existing single, temporal-transition and
  comparison workflows behave the same.
- Installer / packaging not changed in this release.

## [1.0.0] - 2025
- Initial public release.
