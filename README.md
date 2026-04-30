[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19928497.svg)](https://doi.org/10.5281/zenodo.19928497)

# LUMA

**LUMA** (Land Use & Land Cover Analyzer) is a desktop software tool for land use and land cover analysis based on geospatial raster data. It supports local GeoTIFF files and compatible remote datasets, enabling buffer-based analysis from geographic coordinates, class distribution summaries, landscape metrics, multi-point comparison, and temporal change assessment.

Public repository: <https://github.com/amgoncalvesusp/LUMA>

Current release: <https://github.com/amgoncalvesusp/LUMA/releases/tag/v1.0.0>

Zenodo DOI: <https://doi.org/10.5281/zenodo.19928497>

## Main features

- Land use and land cover analysis using a central coordinate and buffer radius.
- Support for local GeoTIFF raster files (`.tif` / `.tiff`).
- Support for compatible remote datasets, including ESA WorldCover.
- Legend support for MapBiomas, ESA WorldCover, Copernicus Global Land Cover, MODIS, and Dynamic World.
- Calculation of class area, percentage, valid pixels, and total area.
- Landscape metrics, including Shannon diversity, Simpson diversity, patch count, patch density, largest patch index, aggregation, contagion, mean shape index, and impervious surface area index.
- Temporal analysis for two-date comparison or multi-year series.
- Multi-point comparison using manual input, pasted tables, CSV, or Excel files.
- Export of results to CSV, Excel, JSON, PDF, and TIFF for comparative maps.

## Download

### Recommended option: GitHub Release

1. Open the release page:
   <https://github.com/amgoncalvesusp/LUMA/releases/tag/v1.0.0>
2. Download `LUMA_ULTIMA.rar` from the **Assets** section.
3. Extract the package to a local folder.
4. Run `LUMA.exe`.

### Repository clone

This repository uses **Git LFS** to store large binary files such as DLLs and executables. To clone it correctly:

```powershell
git lfs install
git clone https://github.com/amgoncalvesusp/LUMA.git
cd LUMA
git lfs pull
```

Then run:

```powershell
.\LUMA.exe
```

Avoid relying only on **Code > Download ZIP** when you need the full executable distribution, because files tracked by Git LFS may be downloaded as pointer files instead of real binaries.

## Requirements

- Windows 10 or later.
- Enough disk space for the full distribution package.
- Internet access for remote datasets or external data download.
- Git and Git LFS installed if you intend to clone the repository.

The distribution package already includes the executable and the runtime libraries required for local execution. Python installation is not required to use this distributed version.

## How to use

1. Open `LUMA.exe`.
2. Enter latitude and longitude in decimal degrees.
   Example: Sao Paulo can be represented as latitude `-23.55` and longitude `-46.63`.
3. Define the buffer radius in meters.
4. Choose the data source:
   - **Local File** to use a GeoTIFF raster already stored on your machine.
   - **Remote Dataset** to use a compatible remote source.
5. Choose the appropriate legend or use automatic detection when the file name allows it.
6. Click **Analyze**.
7. Review the results in the application tabs.
8. Use the **File** menu to export outputs.

## Data input

### Local files

Use GeoTIFF raster files (`.tif` or `.tiff`) containing land use and land cover classes. The raster should cover the analysis area and use a recognized coordinate reference system.

Supported legend families include:

- MapBiomas Brazil, Collections 9 and 10
- MapBiomas Amazonia, Atlantic Forest, and Chaco
- ESA WorldCover 2020 and 2021
- Copernicus Global Land Cover
- MODIS Land Cover MCD12Q1
- Google Dynamic World
- Global Forest Watch / Hansen

### Remote datasets

When a remote source is available, LUMA downloads only the area required for the selected buffer. This mode requires an internet connection.

## Available analyses

### Single analysis

Calculates land cover distribution within the selected buffer:

- area in km2 and hectares;
- class percentage;
- number of valid pixels;
- landscape metrics;
- quality warnings when resolution or coverage is insufficient.

### Temporal analysis

Allows comparison of rasters from different years:

- transition matrix between classes;
- persistence;
- net change by class;
- FAO annual deforestation rate;
- multi-year time series.

### Multi-point comparison

Allows comparison of multiple locations in the same workflow:

- manual point entry;
- pasted tables;
- CSV or Excel import;
- column mapping for name, latitude, longitude, and radius;
- TIFF export for comparative maps.

## Export

LUMA can export results to:

- CSV
- Excel (`.xlsx`)
- JSON
- PDF
- TIFF for comparative maps

These outputs support technical reporting, reproducible analysis workflows, comparison between areas, and result archiving.

## GitHub distribution

The project is publicly distributed through GitHub:

<https://github.com/amgoncalvesusp/LUMA>

Version `v1.0.0` is available as a GitHub Release:

<https://github.com/amgoncalvesusp/LUMA/releases/tag/v1.0.0>

Because the Windows distribution contains large runtime libraries, the repository uses Git LFS. This allows versioning of files that exceed normal GitHub blob size limits.

For end users, the recommended path is downloading the packaged release from **Releases**. For developers or users who need to clone the repository, Git LFS is required.

## Citation

If you use LUMA in research, technical reports, or derived workflows, cite the software using the Zenodo DOI:

`10.5281/zenodo.19928497`

## How to cite

Recommended citation:

Goncalves, A. M., and Gorni, G. R. LUMA: Land Use & Land Cover Analyzer. Zenodo. <https://doi.org/10.5281/zenodo.19928497>

BibTeX:

```bibtex
@software{goncalves_gorni_luma_2026,
  author = {Goncalves, Adriano Marques and Gorni, Guilherme Rossi},
  title = {LUMA: Land Use \& Land Cover Analyzer},
  year = {2026},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.19928497},
  url = {https://doi.org/10.5281/zenodo.19928497}
}
```

## Authors

- Adriano Marques Goncalves (UNIARA)
- Guilherme Rossi Gorni (UNIARA)

## License

Apache License 2.0
