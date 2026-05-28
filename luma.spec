# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for LUMA

import os
import sys
from pathlib import Path

block_cipher = None

# Locate the package
pkg_dir = os.path.join(os.getcwd(), "luma")
app_icon = os.path.join(pkg_dir, "resources", "icons", "brazil_map.ico")

# Find PySide6 WebEngine resources
import PySide6
pyside6_dir = os.path.dirname(PySide6.__file__)
webengine_locales = os.path.join(pyside6_dir, "translations", "qtwebengine_locales")
webengine_resources = os.path.join(pyside6_dir, "resources")

extra_datas = [
    (os.path.join(pkg_dir, "i18n", "*.yaml"), "luma/i18n"),
    (os.path.join(pkg_dir, "legends", "*.yaml"), "luma/legends"),
    (os.path.join(pkg_dir, "sources", "*.yaml"), "luma/sources"),
    (os.path.join(pkg_dir, "resources"), "luma/resources"),
]

# Add WebEngine locales if they exist
if os.path.isdir(webengine_locales):
    extra_datas.append((webengine_locales, "PySide6/translations/qtwebengine_locales"))
if os.path.isdir(webengine_resources):
    extra_datas.append((webengine_resources, "PySide6/resources"))

# Add QtWebEngineProcess.exe (critical for WebEngine in frozen builds)
webengine_proc = os.path.join(pyside6_dir, "QtWebEngineProcess.exe")
if os.path.isfile(webengine_proc):
    extra_datas.append((webengine_proc, "PySide6"))

# Add Qt platform plugins explicitly (critical for frozen builds)
qt_platforms = os.path.join(pyside6_dir, "plugins", "platforms")
if os.path.isdir(qt_platforms):
    extra_datas.append((qt_platforms, "PySide6/plugins/platforms"))
qt_styles = os.path.join(pyside6_dir, "plugins", "styles")
if os.path.isdir(qt_styles):
    extra_datas.append((qt_styles, "PySide6/plugins/styles"))
qt_imageformats = os.path.join(pyside6_dir, "plugins", "imageformats")
if os.path.isdir(qt_imageformats):
    extra_datas.append((qt_imageformats, "PySide6/plugins/imageformats"))

# Add proj database for pyproj
import pyproj
proj_dir = os.path.join(os.path.dirname(pyproj.__file__), "proj_dir", "share", "proj")
if os.path.isdir(proj_dir):
    extra_datas.append((proj_dir, "proj"))
else:
    # Try alternative location
    proj_data = pyproj.datadir.get_data_dir()
    if os.path.isdir(proj_data):
        extra_datas.append((proj_data, "proj"))

# Add rasterio/GDAL data
import rasterio
gdal_data = os.environ.get("GDAL_DATA", "")
if gdal_data and os.path.isdir(gdal_data):
    extra_datas.append((gdal_data, "gdal"))
else:
    rasterio_dir = os.path.dirname(rasterio.__file__)
    gdal_data_candidate = os.path.join(rasterio_dir, "gdal_data")
    if os.path.isdir(gdal_data_candidate):
        extra_datas.append((gdal_data_candidate, "gdal"))

a = Analysis(
    [os.path.join(pkg_dir, "main.py")],
    pathex=[os.getcwd()],
    binaries=[],
    datas=extra_datas,
    hiddenimports=[
        # rasterio — all submodules (Cython extensions are often missed)
        "rasterio", "rasterio._base", "rasterio._env", "rasterio._err",
        "rasterio._features", "rasterio._filepath", "rasterio._fill",
        "rasterio._io", "rasterio._path", "rasterio._transform",
        "rasterio._version", "rasterio._vsiopener", "rasterio._warp",
        "rasterio.abc", "rasterio.control", "rasterio.coords",
        "rasterio.crs", "rasterio.drivers", "rasterio.dtypes",
        "rasterio.enums", "rasterio.env", "rasterio.errors",
        "rasterio.features", "rasterio.fill", "rasterio.io",
        "rasterio.mask", "rasterio.merge", "rasterio.path",
        "rasterio.profiles", "rasterio.rpc", "rasterio.sample",
        "rasterio.serde", "rasterio.session", "rasterio.shutil",
        "rasterio.tools", "rasterio.transform", "rasterio.vrt",
        "rasterio.warp", "rasterio.windows",
        # numpy / scipy
        "numpy", "scipy", "scipy.ndimage",
        # shapely
        "shapely", "shapely.geometry",
        # pyproj
        "pyproj", "pyproj.database",
        # other
        "yaml", "httpx", "httpx._transports",
        "PIL", "folium", "folium.plugins",
        "reportlab", "reportlab.lib", "reportlab.platypus",
        "exactextract",
        # openpyxl for Excel import/export
        "openpyxl", "openpyxl.workbook", "openpyxl.worksheet",
        "openpyxl.styles", "openpyxl.reader", "openpyxl.writer",
    ],
    hookspath=[os.path.join(os.getcwd(), "hooks")],
    hooksconfig={},
    runtime_hooks=[os.path.join(os.getcwd(), "hooks", "pyi_rth_qt_plugins.py")],
    excludes=[
        "tkinter",
        "matplotlib.backends.backend_tkagg",
        "PyQt5", "PyQt6", "PyQt4",
        "IPython", "jupyter", "notebook",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LUMA",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=app_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="LUMA",
)

# ── Post-build: copy Qt platform plugins and DLLs next to the .exe ────────
import shutil

# Post-build: copy Qt platform plugins and DLLs next to the .exe.
# This keeps the app portable on machines without PySide6/Qt installed and
# avoids loading platform plugins from unrelated software in PATH.
dist_root = globals().get("DISTPATH", "dist")
dist_dir = os.path.join(dist_root, "LUMA")
if os.path.isdir(dist_dir):
    src_plugins = os.path.join(pyside6_dir, "plugins")
    dst_plugins = os.path.join(dist_dir, "plugins")
    if os.path.isdir(src_plugins):
        if os.path.isdir(dst_plugins):
            shutil.rmtree(dst_plugins)
        shutil.copytree(src_plugins, dst_plugins)
        print(f"[POST-BUILD] Copied plugins/ to {dst_plugins}")

    # Qt also checks ./platforms beside the executable; keep that layout too.
    src_platforms = os.path.join(src_plugins, "platforms")
    dst_platforms = os.path.join(dist_dir, "platforms")
    if os.path.isdir(src_platforms):
        if os.path.isdir(dst_platforms):
            shutil.rmtree(dst_platforms)
        shutil.copytree(src_platforms, dst_platforms)
        print(f"[POST-BUILD] Copied platforms/ to {dst_platforms}")

    for pattern in (
        "Qt6*.dll", "pyside6*.dll", "shiboken6*.dll", "opengl32sw.dll",
        "D3DCOMPILER_47.dll", "libEGL.dll", "libGLESv2.dll",
        "vcruntime*.dll", "msvcp*.dll", "concrt140.dll",
    ):
        for src in Path(pyside6_dir).glob(pattern):
            if src.is_file():
                shutil.copy2(src, os.path.join(dist_dir, src.name))
                print(f"[POST-BUILD] Copied {src.name}")

    qt_conf = os.path.join(dist_dir, "qt.conf")
    with open(qt_conf, "w", encoding="ascii") as f:
        f.write("[Paths]\n")
        f.write("Prefix = .\n")
        f.write("Plugins = plugins\n")
        f.write("Translations = _internal/PySide6/translations\n")
    print(f"[POST-BUILD] Wrote {qt_conf}")
