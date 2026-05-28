"""PyInstaller hook to fix QtWebEngine locales path for PySide6."""

import os
from PyInstaller.utils.hooks import collect_data_files

# Collect WebEngine data from the correct PySide6 location
datas = collect_data_files("PySide6", includes=["translations/qtwebengine_locales/**"])
