"""Interactive map viewer using Folium + QWebEngineView (lazy-loaded)."""

from __future__ import annotations

import json
import base64
import html
import io

import numpy as np
from PIL import Image, ImageColor
from rasterio.transform import array_bounds
from rasterio.warp import transform_bounds
from pyproj import CRS
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import QUrl, Qt


class MapViewer(QWidget):
    """Displays an interactive Leaflet map showing the buffer and results.

    QWebEngineView is imported and created lazily — on first use — to avoid
    blocking the application startup in frozen (PyInstaller) builds.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # Placeholder shown until map is first requested
        self._placeholder = QLabel("Map will appear here after analysis")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            "background: #ecf0f1; color: #7f8c8d; font-size: 14px; padding: 40px;"
        )
        self._layout.addWidget(self._placeholder)

        self._web = None  # Created lazily
        self._web_failed = False  # Track if WebEngine init failed
        self._temp_file: str | None = None

    def _ensure_web(self) -> bool:
        """Create the QWebEngineView on first use. Returns False on failure."""
        if self._web is not None:
            return True
        if self._web_failed:
            return False
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView

            self._web = QWebEngineView()
            self._placeholder.setVisible(False)
            self._layout.removeWidget(self._placeholder)
            self._layout.addWidget(self._web)
            return True
        except Exception as exc:
            self._web_failed = True
            self._placeholder.setText(
                f"Map unavailable (WebEngine error)\n{exc}"
            )
            return False

    def show_default(self) -> None:
        """Show a default world map."""
        if not self._ensure_web():
            return
        html = self._build_map_html(0, 0, 2)
        self._load_html(html)

    def show_buffer(
        self,
        lat: float,
        lon: float,
        radius_m: float,
        geojson_buffer: dict | None = None,
    ) -> None:
        """Show the map centred on the coordinate with the buffer drawn."""
        if not self._ensure_web():
            return
        zoom = self._estimate_zoom(radius_m)
        html = self._build_map_html(lat, lon, zoom, radius_m, geojson_buffer)
        self._load_html(html)

    def show_aoi(
        self,
        aoi_or_geojson,
        *,
        center: tuple[float, float] | None = None,
        zoom: int = 12,
    ) -> None:
        """Display a polygonal AOI on the map.

        The method accepts an ``AOI`` instance or a WGS-84 GeoJSON geometry,
        allowing the drawing widget to be integrated without changing the
        existing buffer/results methods.
        """
        if not self._ensure_web() or aoi_or_geojson is None:
            return
        if hasattr(aoi_or_geojson, "to_geojson"):
            geojson = aoi_or_geojson.to_geojson()
            if center is None and hasattr(aoi_or_geojson, "centroid_wgs84"):
                center = aoi_or_geojson.centroid_wgs84
        else:
            geojson = aoi_or_geojson
        if center is None:
            from shapely.geometry import shape

            centroid = shape(geojson).centroid
            center = (centroid.y, centroid.x)
        lat, lon = center
        html = self._build_map_html(lat, lon, zoom, geojson_buffer=geojson)
        self._load_html(html)

    def show_results(
        self,
        lat: float,
        lon: float,
        radius_m: float,
        class_stats: list,
        geojson_buffer: dict | None = None,
        raster_data=None,
        raster_valid_mask=None,
        raster_transform=None,
        raster_crs=None,
    ) -> None:
        """Show the analysed area with a thematic raster and legend."""
        if not self._ensure_web():
            return
        zoom = self._estimate_zoom(radius_m)
        legend_html = self._build_legend_html(class_stats)
        if all(value is not None for value in (
            raster_data, raster_valid_mask, raster_transform, raster_crs
        )):
            colors = {cs.class_id: cs.color for cs in class_stats}
            legend_html = self._build_classified_overlay_html(
                raster_data, raster_valid_mask, raster_transform, raster_crs,
                colors,
            ) + legend_html
        html = self._build_map_html(
            lat, lon, zoom, radius_m, geojson_buffer, legend_html
        )
        self._load_html(html)

    @staticmethod
    def _build_classified_overlay_html(
        data: np.ndarray,
        valid_mask: np.ndarray,
        transform,
        crs,
        colors: dict[int, str],
    ) -> str:
        """Build a transparent PNG Leaflet overlay from a classified raster."""
        if data.ndim != 2 or valid_mask.shape != data.shape:
            raise ValueError("Raster data and valid mask must be matching 2-D arrays")
        rgba = np.zeros((*data.shape, 4), dtype=np.uint8)
        for class_id, color in colors.items():
            try:
                rgb = ImageColor.getrgb(str(color))
            except ValueError:
                rgb = (128, 128, 128)
            class_mask = (data == class_id) & valid_mask
            rgba[class_mask, 0] = rgb[0]
            rgba[class_mask, 1] = rgb[1]
            rgba[class_mask, 2] = rgb[2]
            rgba[class_mask, 3] = 190

        image = Image.fromarray(rgba, mode="RGBA")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

        height, width = data.shape
        west, south, east, north = array_bounds(height, width, transform)
        source_crs = CRS.from_user_input(crs)
        if not source_crs.is_geographic:
            west, south, east, north = transform_bounds(
                source_crs, CRS.from_epsg(4326), west, south, east, north,
                densify_pts=21,
            )
        bounds = json.dumps([[south, west], [north, east]])
        return (
            "<script>"
            f"L.imageOverlay('data:image/png;base64,{encoded}', {bounds}, "
            "{opacity: 0.72, interactive: false}).addTo(map);"
            "</script>"
        )

    def _estimate_zoom(self, radius_m: float) -> int:
        if radius_m > 100_000:
            return 6
        if radius_m > 50_000:
            return 7
        if radius_m > 20_000:
            return 9
        if radius_m > 10_000:
            return 10
        if radius_m > 5_000:
            return 11
        if radius_m > 1_000:
            return 13
        return 14

    def _build_legend_html(self, class_stats: list) -> str:
        if not class_stats:
            return ""
        rows = ""
        for cs in class_stats[:15]:
            rows += (
                f'<tr><td style="width:14px;height:14px;'
                f'background:{cs.color};border:1px solid #999;"></td>'
                f'<td style="padding-left:6px;font-size:11px;">'
                f'{cs.class_name} ({cs.percentage:.1f}%)</td></tr>'
            )
        return f"""
        <div style="position:fixed;bottom:30px;right:15px;z-index:9999;
                    background:rgba(255,255,255,0.92);padding:10px 14px;
                    border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.25);
                    max-height:350px;overflow-y:auto;font-family:sans-serif;">
            <table>{rows}</table>
        </div>
        """

    def _build_map_html(
        self,
        lat: float,
        lon: float,
        zoom: int,
        radius_m: float | None = None,
        geojson_buffer: dict | None = None,
        extra_html: str = "",
    ) -> str:
        buffer_js = ""
        if radius_m and geojson_buffer is None:
            buffer_js = f"""
            L.circle([{lat}, {lon}], {{
                radius: {radius_m},
                color: '#e74c3c',
                weight: 2,
                fillColor: '#e74c3c',
                fillOpacity: 0.12
            }}).addTo(map);
            L.marker([{lat}, {lon}]).addTo(map);
            """
        elif geojson_buffer:
            gj = json.dumps(geojson_buffer)
            buffer_js = f"""
            L.geoJSON({gj}, {{
                style: {{color: '#e74c3c', weight: 2, fillColor: '#e74c3c', fillOpacity: 0.12}}
            }}).addTo(map);
            L.marker([{lat}, {lon}]).addTo(map);
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8"/>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                html, body, #map {{ height: 100%; margin: 0; padding: 0; }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            {extra_html}
            <script>
                var map = L.map('map').setView([{lat}, {lon}], {zoom});
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '&copy; OpenStreetMap contributors',
                    maxZoom: 19
                }}).addTo(map);

                L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                    attribution: '&copy; Esri',
                    maxZoom: 19
                }});

                var baseMaps = {{
                    "Streets": L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png'),
                    "Satellite": L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}')
                }};
                L.control.layers(baseMaps).addTo(map);

                {buffer_js}
            </script>
        </body>
        </html>
        """

    @staticmethod
    def _build_compare_aois_html(areas: list[dict]) -> str:
        """Build a Leaflet map using the exact WGS-84 AOI polygons."""
        palette = [
            "#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
            "#1abc9c", "#e67e22", "#34495e", "#e91e63", "#00bcd4",
        ]
        features = []
        for index, item in enumerate(areas):
            aoi = item["aoi"]
            features.append({
                "type": "Feature",
                "properties": {
                    "label": str(item.get("label", f"Área {index + 1}")),
                    "color": palette[index % len(palette)],
                },
                "geometry": aoi.to_geojson(),
            })
        feature_collection = json.dumps(
            {"type": "FeatureCollection", "features": features},
            ensure_ascii=False,
        )
        return f"""
        <!DOCTYPE html>
        <html><head><meta charset="utf-8"/>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>html, body, #map {{ height: 100%; margin: 0; padding: 0; }}</style>
        </head><body><div id="map"></div><script>
        var map = L.map('map');
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; OpenStreetMap contributors', maxZoom: 19
        }}).addTo(map);
        var areas = {feature_collection};
        var layer = L.geoJSON(areas, {{
            style: function(feature) {{ return {{
                color: feature.properties.color, weight: 3,
                fillColor: feature.properties.color, fillOpacity: 0.22
            }}; }},
            onEachFeature: function(feature, layer) {{
                layer.bindTooltip(feature.properties.label, {{sticky: true}});
                layer.bindPopup(feature.properties.label);
            }}
        }}).addTo(map);
        if (layer.getBounds().isValid()) {{ map.fitBounds(layer.getBounds(), {{padding: [20, 20]}}); }}
        </script></body></html>
        """

    def show_compare_aois(self, areas: list[dict]) -> None:
        """Show exact AOI polygons; each item contains ``label`` and ``aoi``."""
        if not self._ensure_web() or not areas:
            return
        self._load_html(self._build_compare_aois_html(areas))

    def show_compare_points(self, points_data: list[dict]) -> None:
        """Show all compared points on the map with buffers, scale bar and north arrow.

        Each dict must have: label, lat, lon, radius_m.
        """
        if not self._ensure_web() or not points_data:
            return

        # Compute map centre and appropriate zoom
        lats = [p["lat"] for p in points_data]
        lons = [p["lon"] for p in points_data]
        centre_lat = (min(lats) + max(lats)) / 2
        centre_lon = (min(lons) + max(lons)) / 2
        max_r = max(p["radius_m"] for p in points_data)
        zoom = self._estimate_zoom(max_r)

        # Distinct colours for up to 10 points
        palette = [
            "#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
            "#1abc9c", "#e67e22", "#34495e", "#e91e63", "#00bcd4",
        ]

        markers_js = ""
        for i, p in enumerate(points_data):
            color = palette[i % len(palette)]
            # Labels are user supplied; escape HTML and JavaScript delimiters
            # before embedding them in the Leaflet document.
            label = html.escape(str(p["label"]), quote=True)
            label = label.replace("\\", "\\\\").replace("\r", " ").replace("\n", " ")
            label = label.replace("'", "\\'")
            markers_js += f"""
            L.circle([{p['lat']}, {p['lon']}], {{
                radius: {p['radius_m']},
                color: '{color}',
                weight: 2,
                fillColor: '{color}',
                fillOpacity: 0.12
            }}).addTo(map);
            L.marker([{p['lat']}, {p['lon']}], {{
                icon: L.divIcon({{
                    className: '',
                    html: '<div style="background:rgba(255,255,255,0.96);color:#111;'
                        + 'padding:3px 7px 3px 9px;border:1px solid #111;'
                        + 'border-left:5px solid {color};border-radius:3px;font-size:12px;'
                        + 'font-weight:800;white-space:nowrap;'
                        + 'text-shadow:0 1px 0 #fff;'
                        + 'box-shadow:0 2px 8px rgba(0,0,0,0.65);">'
                        + '{label}</div>',
                    iconAnchor: [0, 0]
                }})
            }}).addTo(map).bindPopup('{label}');
            """

        north_arrow_html = """
        <div id="north-arrow" style="position:fixed;top:70px;right:15px;z-index:9999;
             background:rgba(255,255,255,0.85);border-radius:50%;width:44px;height:44px;
             display:flex;align-items:center;justify-content:center;
             box-shadow:0 2px 6px rgba(0,0,0,0.3);">
            <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
                <polygon points="16,2 20,18 16,14 12,18" fill="#e74c3c"/>
                <polygon points="16,30 12,14 16,18 20,14" fill="#555"/>
                <text x="16" y="9" text-anchor="middle" font-size="7"
                      font-family="sans-serif" font-weight="bold" fill="white">N</text>
            </svg>
        </div>
        """

        document_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8"/>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                html, body, #map {{ height: 100%; margin: 0; padding: 0; }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            {north_arrow_html}
            <script>
                var map = L.map('map').setView([{centre_lat}, {centre_lon}], {zoom});
                var streets = L.tileLayer(
                    'https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
                    {{attribution: '&copy; OpenStreetMap contributors', maxZoom: 19}}
                ).addTo(map);
                var satellite = L.tileLayer(
                    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
                    {{attribution: '&copy; Esri', maxZoom: 19}}
                );
                L.control.layers({{"Streets": streets, "Satellite": satellite}}).addTo(map);
                L.control.scale({{imperial: false}}).addTo(map);
                {markers_js}
            </script>
        </body>
        </html>
        """
        self._load_html(document_html)

    def grab_map(self):
        """Return a QPixmap of the current map view (for TIFF / PDF export)."""
        if self._web is None:
            return None
        return self._web.grab()

    def export_tiff_with_legend(
        self,
        path: str,
        class_stats: list | None = None,
        title: str = "",
    ) -> bool:
        """Save the current map as a TIFF with an optional legend strip."""
        pixmap = self.grab_map()
        if pixmap is None or pixmap.isNull():
            return False
        try:
            from PySide6.QtCore import QBuffer, QIODevice
            from PIL import Image, ImageDraw, ImageFont
            from io import BytesIO

            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            pixmap.save(buffer, "PNG")
            map_image = Image.open(BytesIO(bytes(buffer.data()))).convert("RGB")
            rows = list(class_stats or [])[:16]
            row_height = 22
            legend_height = max(60, 40 + row_height * max(len(rows), 1))
            output = Image.new(
                "RGB", (map_image.width, map_image.height + legend_height), "white"
            )
            output.paste(map_image, (0, 0))
            draw = ImageDraw.Draw(output)
            try:
                font = ImageFont.truetype("arial.ttf", 13)
                bold_font = ImageFont.truetype("arialbd.ttf", 14)
            except Exception:
                font = ImageFont.load_default()
                bold_font = font
            y = map_image.height + 8
            if title:
                draw.text((12, y), title, fill="black", font=bold_font)
                y += 22
            for stats in rows:
                color = getattr(stats, "color", "#888")
                name = getattr(stats, "class_name", str(stats))
                percentage = getattr(stats, "percentage", None)
                draw.rectangle([12, y + 4, 28, y + 18], fill=color, outline="black")
                label = name + (f"  ({percentage:.1f}%)" if percentage is not None else "")
                draw.text((36, y + 2), label, fill="black", font=font)
                y += row_height
            output.save(path, format="TIFF")
            return True
        except Exception:
            return pixmap.save(path, "TIFF")

    def _load_html(self, html: str) -> None:
        # Use setHtml with a base URL so the CDN scripts can load
        self._web.setHtml(html, QUrl("https://unpkg.com/"))
