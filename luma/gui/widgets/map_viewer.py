"""Interactive map viewer using Folium + QWebEngineView (lazy-loaded)."""

from __future__ import annotations

import json

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

    def show_results(
        self,
        lat: float,
        lon: float,
        radius_m: float,
        class_stats: list,
        geojson_buffer: dict | None = None,
    ) -> None:
        """Show buffer with a legend overlay of results."""
        if not self._ensure_web():
            return
        zoom = self._estimate_zoom(radius_m)
        legend_html = self._build_legend_html(class_stats)
        html = self._build_map_html(
            lat, lon, zoom, radius_m, geojson_buffer, legend_html
        )
        self._load_html(html)

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

        try:
            from luma.core.crs_utils import optimal_utm_crs
            epsg_code = optimal_utm_crs(lon, lat).to_epsg() if (lat or lon) else "—"
        except Exception:
            epsg_code = "—"
        epsg_html = f"""
        <div style="position:fixed;top:15px;left:60px;z-index:9999;
             background:rgba(255,255,255,0.92);padding:4px 10px;border-radius:4px;
             font-family:sans-serif;font-size:12px;font-weight:bold;color:#222;
             box-shadow:0 2px 6px rgba(0,0,0,0.2);">EPSG: {epsg_code} (UTM)</div>
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
            {epsg_html}
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

    def show_compare_points(
        self,
        points_data: list[dict],
        gradient_values: list[float] | None = None,
        gradient_label: str = "",
    ) -> None:
        """Show all compared points on the map with buffers, scale bar and north arrow.

        Each dict must have: label, lat, lon, radius_m.
        Optional gradient_values colors point fills by metric value.
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

        def _grad_color(v: float, vmin: float, vmax: float) -> str:
            span = (vmax - vmin) or 1.0
            t_ = (v - vmin) / span
            r = int(40 + 200 * t_)
            g = int(120 * (1 - abs(0.5 - t_) * 2))
            b = int(220 * (1 - t_))
            return f"rgb({r},{g},{b})"

        use_grad = gradient_values is not None and len(gradient_values) == len(points_data)
        if use_grad:
            vmin = min(gradient_values); vmax = max(gradient_values)

        markers_js = ""
        for i, p in enumerate(points_data):
            if use_grad:
                color = _grad_color(gradient_values[i], vmin, vmax)
            else:
                color = palette[i % len(palette)]
            label = p["label"].replace("'", "\\'")
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

        # EPSG (UTM) for the centroid
        try:
            from luma.core.crs_utils import optimal_utm_crs
            epsg_code = optimal_utm_crs(centre_lon, centre_lat).to_epsg()
        except Exception:
            epsg_code = "—"
        epsg_html = f"""
        <div style="position:fixed;top:15px;left:60px;z-index:9999;
             background:rgba(255,255,255,0.92);padding:4px 10px;border-radius:4px;
             font-family:sans-serif;font-size:12px;font-weight:bold;color:#222;
             box-shadow:0 2px 6px rgba(0,0,0,0.2);">EPSG: {epsg_code} (UTM)</div>
        """

        gradient_legend_html = ""
        if use_grad:
            gradient_legend_html = f"""
            <div style="position:fixed;bottom:30px;left:15px;z-index:9999;
                 background:rgba(255,255,255,0.92);padding:8px 12px;border-radius:6px;
                 font-family:sans-serif;font-size:11px;
                 box-shadow:0 2px 6px rgba(0,0,0,0.25);">
              <div style="font-weight:bold;margin-bottom:4px;">{gradient_label}</div>
              <div style="width:160px;height:12px;background:linear-gradient(
                 to right, rgb(40,0,220), rgb(140,60,110), rgb(240,0,0));"></div>
              <div style="display:flex;justify-content:space-between;font-size:10px;">
                <span>{vmin:.2f}</span><span>{vmax:.2f}</span>
              </div>
            </div>
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

        html = f"""
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
            {epsg_html}
            {gradient_legend_html}
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
        self._load_html(html)

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
        """Save the current map as TIFF with a legend strip appended below."""
        if self._web is None:
            return False
        pix = self._web.grab()
        if pix is None or pix.isNull():
            return False
        try:
            from PySide6.QtCore import QBuffer, QIODevice
            from PIL import Image, ImageDraw, ImageFont
            from io import BytesIO
        except Exception:
            return pix.save(path, "TIFF")

        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        pix.save(buf, "PNG")
        map_img = Image.open(BytesIO(bytes(buf.data()))).convert("RGB")

        rows = list(class_stats or [])[:16]
        row_h = 22
        legend_h = max(60, 40 + row_h * max(len(rows), 1))
        out = Image.new("RGB", (map_img.width, map_img.height + legend_h), "white")
        out.paste(map_img, (0, 0))
        draw = ImageDraw.Draw(out)
        try:
            font = ImageFont.truetype("arial.ttf", 13)
            font_b = ImageFont.truetype("arialbd.ttf", 14)
        except Exception:
            font = ImageFont.load_default()
            font_b = font
        y = map_img.height + 8
        if title:
            draw.text((12, y), title, fill="black", font=font_b)
            y += 22
        for cs in rows:
            color = getattr(cs, "color", "#888")
            name = getattr(cs, "class_name", str(cs))
            pct = getattr(cs, "percentage", None)
            draw.rectangle([12, y + 4, 28, y + 18], fill=color, outline="black")
            txt = f"{name}" + (f"  ({pct:.1f}%)" if pct is not None else "")
            draw.text((36, y + 2), txt, fill="black", font=font)
            y += row_h
        out.save(path, format="TIFF")
        return True

    def _load_html(self, html: str) -> None:
        # Use setHtml with a base URL so the CDN scripts can load
        self._web.setHtml(html, QUrl("https://unpkg.com/"))
