"""PyInstaller runtime hook - set Qt paths before PySide6 loads.

Frozen Qt apps are sensitive to user/system Qt environment variables left by
other software. Always point Qt to the plugins bundled with this executable.
"""

import os
import sys

if getattr(sys, "frozen", False):
    base = sys._MEIPASS  # type: ignore[attr-defined]
    exe_dir = os.path.dirname(sys.executable)

    pyside_dir_candidates = [
        os.path.join(base, "PySide6"),
        os.path.join(exe_dir, "_internal", "PySide6"),
        os.path.join(exe_dir, "PySide6"),
    ]
    pyside_dir = next((p for p in pyside_dir_candidates if os.path.isdir(p)), "")
    shiboken_dir = os.path.join(base, "shiboken6")
    plugin_path = os.path.join(pyside_dir, "plugins")
    platforms_path = os.path.join(plugin_path, "platforms")

    # Avoid picking up Qt plugins from Anaconda, PyMOL, QGIS, or system PATH.
    for key in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "QT_QPA_PLATFORMTHEME"):
        os.environ.pop(key, None)

    path_parts = [
        p for p in (pyside_dir, shiboken_dir, plugin_path, platforms_path, base, exe_dir)
        if p and os.path.isdir(p)
    ]
    os.environ["PATH"] = os.pathsep.join(path_parts + [os.environ.get("PATH", "")])

    for path in path_parts:
        try:
            os.add_dll_directory(path)
        except (AttributeError, OSError):
            pass

    if os.path.isdir(plugin_path):
        os.environ["QT_PLUGIN_PATH"] = plugin_path
    if os.path.isfile(os.path.join(platforms_path, "qwindows.dll")):
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = platforms_path
        os.environ["QT_QPA_PLATFORM"] = "windows"
