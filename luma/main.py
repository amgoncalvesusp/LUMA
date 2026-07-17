"""LUMA application entry point."""

import sys
import os
import traceback

# ── Must run BEFORE any Qt import ─────────────────────────────────────────
if getattr(sys, "frozen", False):
    _base = sys._MEIPASS  # type: ignore[attr-defined]

    # GDAL / Proj
    os.environ.setdefault("PROJ_LIB", os.path.join(_base, "proj"))
    os.environ.setdefault("GDAL_DATA", os.path.join(_base, "gdal"))

    # QtWebEngine: disable Chromium sandbox (causes 0xcc06d007f crash in frozen builds)
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --no-sandbox --disable-software-rasterizer"

    # Point to QtWebEngineProcess.exe inside _internal/PySide6/
    _webengine_proc = os.path.join(_base, "PySide6", "QtWebEngineProcess.exe")
    if os.path.isfile(_webengine_proc):
        os.environ["QTWEBENGINEPROCESS_PATH"] = _webengine_proc

    # Force software OpenGL rendering to avoid GPU driver crashes in frozen builds
    os.environ["QT_OPENGL"] = "software"
    os.environ["QT_QUICK_BACKEND"] = "software"
    os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"

    # Add PySide6 dir to DLL search path (critical for frozen builds)
    _pyside_dir = os.path.join(_base, "PySide6")
    if os.path.isdir(_pyside_dir):
        os.environ["PATH"] = (
            _pyside_dir + os.pathsep + _base + os.pathsep + os.environ.get("PATH", "")
        )
        try:
            os.add_dll_directory(_pyside_dir)
            os.add_dll_directory(_base)
        except (OSError, AttributeError):
            pass

    # Qt platform plugin — try multiple known locations
    _candidates = [
        os.path.join(os.path.dirname(sys.executable), "platforms"),
        os.path.join(_base, "PySide6", "plugins", "platforms"),
        os.path.join(_base, "plugins", "platforms"),
    ]
    for _p in _candidates:
        if os.path.isdir(_p) and os.path.isfile(os.path.join(_p, "qwindows.dll")):
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = _p
            break
    else:
        _plugin_dir = os.path.join(_base, "PySide6", "plugins")
        if os.path.isdir(_plugin_dir):
            os.environ["QT_PLUGIN_PATH"] = _plugin_dir
# ───────────────────────────────────────────────────────────────────────────


def _write_log(msg: str) -> None:
    """Append a diagnostic message to luma_startup.log next to the executable."""
    try:
        log_path = os.path.join(
            os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else ".",
            "luma_startup.log",
        )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def _resource_path(*parts: str) -> str:
    """Resolve bundled resources both in source and PyInstaller builds."""
    candidates: list[str] = []
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        exe_dir = os.path.dirname(sys.executable)
        candidates.extend([
            os.path.join(base, "luma", "resources", *parts),
            os.path.join(exe_dir, "_internal", "luma", "resources", *parts),
            os.path.join(exe_dir, "luma", "resources", *parts),
        ])
    candidates.append(os.path.join(os.path.dirname(__file__), "resources", *parts))
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


def _set_windows_app_id() -> None:
    """Give Windows a stable taskbar identity for the custom icon."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(  # type: ignore[attr-defined]
            "UNIARA.LUMA.BrazilMap"
        )
    except Exception:
        pass


def main() -> None:
    try:
        _write_log("=== LUMA starting ===")
        _write_log(f"frozen={getattr(sys, 'frozen', False)}")
        _write_log(f"executable={sys.executable}")
        _set_windows_app_id()

        _write_log("Importing PySide6.QtWidgets...")
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QIcon
        from PySide6.QtCore import Qt, QLocale

        # Force software OpenGL to prevent GPU driver crashes in frozen builds
        if getattr(sys, "frozen", False):
            _write_log("Setting AA_UseSoftwareOpenGL and AA_ShareOpenGLContexts...")
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)

        _write_log("Creating QApplication...")
        app = QApplication(
            sys.argv if not getattr(sys, "frozen", False) else [sys.executable]
        )
        app.setApplicationName("LUMA")
        app.setOrganizationName("UNIARA")
        app.setApplicationVersion("1.2.0")
        icon_path = _resource_path("icons", "brazil_map.png")
        _write_log(f"Loading icon={icon_path} exists={os.path.exists(icon_path)}")
        app_icon = QIcon(icon_path)
        _write_log(f"icon_is_null={app_icon.isNull()}")
        if not app_icon.isNull():
            app.setWindowIcon(app_icon)

        # Force C locale so numeric widgets always use "." as decimal separator
        # regardless of OS regional settings (prevents Brazilian "," confusion).
        QLocale.setDefault(QLocale(QLocale.Language.C))

        _write_log("Applying stylesheet...")
        app.setStyleSheet(_GLOBAL_STYLE)

        _write_log("Importing MainWindow...")
        from luma.gui.main_window import MainWindow

        _write_log("Creating MainWindow...")
        window = MainWindow()
        if not app_icon.isNull():
            window.setWindowIcon(app_icon)
            _write_log("Window icon applied")
        _write_log("Showing MainWindow...")
        window.show()
        _write_log("Entering event loop...")

        # Install exception hook to catch Qt-level crashes
        def _qt_message_handler(mode, context, message):
            _write_log(f"Qt [{mode}] {context.file}:{context.line} — {message}")

        from PySide6.QtCore import qInstallMessageHandler, QtMsgType
        qInstallMessageHandler(_qt_message_handler)

        sys.exit(app.exec())

    except Exception as exc:
        # Write crash log next to executable
        log_path = os.path.join(
            os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else ".",
            "luma_error.log",
        )
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        _write_log(f"CRASH: {exc}\n{traceback.format_exc()}")
        # Try to show error dialog
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox

            if not QApplication.instance():
                QApplication([sys.executable])
            QMessageBox.critical(None, "LUMA Error", str(exc))
        except Exception:
            pass
        raise


_GLOBAL_STYLE = """
/* ── Base ────────────────────────────────────────────────────────── */
QMainWindow, QDialog {
    background: #f4f6f8;
    font-family: "Segoe UI", "Helvetica", sans-serif;
}
QWidget {
    font-size: 12px;
    color: #2c3e50;
}

/* ── Group boxes ─────────────────────────────────────────────────── */
QGroupBox {
    font-weight: 600;
    border: 1px solid #d5dbe0;
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px 10px 10px 10px;
    background: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 8px;
    color: #2c3e50;
    background: #ffffff;
}

/* ── Tabs ────────────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #d5dbe0;
    border-radius: 6px;
    background: white;
    top: -1px;
}
QTabBar::tab {
    padding: 8px 14px;
    margin-right: 3px;
    border: 1px solid #d5dbe0;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    background: #ecf0f1;
    color: #5d6d7e;
    font-weight: 500;
}
QTabBar::tab:hover {
    background: #e1e6ea;
    color: #2c3e50;
}
QTabBar::tab:selected {
    background: white;
    color: #2c3e50;
    font-weight: 700;
    border-bottom: 2px solid #3498db;
    margin-bottom: -1px;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
QPushButton {
    padding: 6px 16px;
    border-radius: 5px;
    border: 1px solid #bdc3c7;
    background: #ffffff;
    color: #2c3e50;
    font-weight: 500;
    min-height: 20px;
}
QPushButton:hover {
    background: #ecf0f1;
    border-color: #95a5a6;
}
QPushButton:pressed {
    background: #d5dbe0;
}
QPushButton:focus {
    border: 2px solid #2980b9;
}
QPushButton:disabled {
    color: #bdc3c7;
    background: #f8f9fa;
    border-color: #ecf0f1;
}

/* ── Input fields ────────────────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
    padding: 4px 8px;
    border: 1px solid #d5dbe0;
    border-radius: 4px;
    background: white;
    selection-background-color: #3498db;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QPlainTextEdit:focus {
    border-color: #3498db;
    outline: none;
}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled,
QDoubleSpinBox:disabled {
    background: #f8f9fa;
    color: #95a5a6;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}

/* ── Tables ──────────────────────────────────────────────────────── */
QTableWidget {
    gridline-color: #ecf0f1;
    font-size: 12px;
    background: white;
    border: 1px solid #d5dbe0;
    border-radius: 4px;
    alternate-background-color: #fafbfc;
}
QTableWidget::item {
    padding: 5px 8px;
}
QTableWidget::item:selected {
    background: #d6eaf8;
    color: #2c3e50;
}
QHeaderView::section {
    background: #34495e;
    color: white;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid #2c3e50;
    font-weight: 600;
    font-size: 11px;
}
QHeaderView::section:last {
    border-right: none;
}

/* ── Radio buttons & checkboxes ──────────────────────────────────── */
QRadioButton, QCheckBox {
    spacing: 6px;
    color: #2c3e50;
}
QRadioButton::indicator, QCheckBox::indicator {
    width: 15px;
    height: 15px;
}

/* ── Status bar ──────────────────────────────────────────────────── */
QStatusBar {
    background: #2c3e50;
    color: white;
    font-size: 12px;
    padding: 4px 10px;
}
QStatusBar::item {
    border: none;
}

/* ── Menu bar ────────────────────────────────────────────────────── */
QMenuBar {
    background: #2c3e50;
    color: white;
    padding: 2px;
}
QMenuBar::item {
    padding: 6px 12px;
    background: transparent;
}
QMenuBar::item:selected {
    background: #34495e;
    border-radius: 3px;
}
QMenu {
    background: white;
    border: 1px solid #d5dbe0;
    padding: 4px;
}
QMenu::item {
    padding: 6px 24px;
    border-radius: 3px;
}
QMenu::item:selected {
    background: #3498db;
    color: white;
}
QMenu::separator {
    height: 1px;
    background: #ecf0f1;
    margin: 4px 8px;
}

/* ── Scrollbars ──────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #f4f6f8;
    width: 12px;
    border: none;
}
QScrollBar::handle:vertical {
    background: #bdc3c7;
    border-radius: 5px;
    min-height: 20px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background: #95a5a6;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #f4f6f8;
    height: 12px;
    border: none;
}
QScrollBar::handle:horizontal {
    background: #bdc3c7;
    border-radius: 5px;
    min-width: 20px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover {
    background: #95a5a6;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Tooltips ────────────────────────────────────────────────────── */
QToolTip {
    background: #2c3e50;
    color: white;
    border: 1px solid #34495e;
    padding: 8px 10px;
    border-radius: 4px;
    font-size: 12px;
    max-width: 400px;
    opacity: 240;
}
"""


if __name__ == "__main__":
    main()
