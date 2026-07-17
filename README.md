# LUMA - Land Use & Land Cover Analyzer

Raster-based LULC analysis with coordinate buffer zones, landscape metrics, and multi-temporal change detection.

## Implemented workflows

- Single-site analysis using a coordinate/radius buffer or a polygonal AOI.
- AOI drawing and import from GeoJSON, KML/KMZ, and polygon Shapefile.
- MapBiomas Brazil Collection 10.1 (30 m, 1985–2024) and Collection 3 beta
  (10 m, 2017–2024), with year validation and remote COG access.
- Temporal transition and time-series analysis with raster alignment.
- Comparison of points or multiple polygonal AOIs, including exact Leaflet
  geometry overlays and PDF/JSON/Excel export.
- Versioned `.luma.json` project files for reproducible academic workflows.

## Running tests

```text
pytest -q
```

The application defaults to Brazilian Portuguese and keeps English available
through the settings menu.

## Authors

- Adriano Marques Gonçalves (UNIARA)
- Guilherme Rossi Gorni (UNIARA)

## License

Apache License 2.0
