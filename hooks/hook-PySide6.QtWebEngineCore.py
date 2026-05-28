"""Override PyInstaller's default QtWebEngineCore hook.

Handles PySide6 installed via pip (site-packages layout) rather than
Qt's Library/ layout expected by the default hook.
"""

import os
from PyInstaller.utils.hooks import collect_data_files

import PySide6
pyside6_dir = os.path.dirname(PySide6.__file__)

datas = []
binaries = []

# WebEngine locales
locales = os.path.join(pyside6_dir, "translations", "qtwebengine_locales")
if os.path.isdir(locales):
    datas.append((locales, os.path.join("PySide6", "translations", "qtwebengine_locales")))

# WebEngine resources
resources = os.path.join(pyside6_dir, "resources")
if os.path.isdir(resources):
    datas.append((resources, os.path.join("PySide6", "resources")))

# QtWebEngineProcess executable
for name in ["QtWebEngineProcess.exe", "QtWebEngineProcess"]:
    proc = os.path.join(pyside6_dir, name)
    if os.path.isfile(proc):
        binaries.append((proc, "."))
        break
