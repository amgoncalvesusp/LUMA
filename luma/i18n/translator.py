"""Lightweight i18n system — YAML-based translations with instant switching."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

I18N_DIR = Path(__file__).parent
_current_lang: str = "en"
_translations: dict[str, dict[str, str]] = {}

AVAILABLE_LANGUAGES = {
    "en": "English",
    "pt_BR": "Português (Brasil)",
}


def load_language(lang: str) -> dict[str, str]:
    """Load a translation file and return the flat key-value mapping."""
    path = I18N_DIR / f"{lang}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Translation file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # Flatten nested dicts with dot notation
    return _flatten(data)


def _flatten(d: dict, prefix: str = "") -> dict[str, str]:
    """Flatten a nested dict: {"a": {"b": "c"}} -> {"a.b": "c"}."""
    items: dict[str, str] = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            items.update(_flatten(v, key))
        else:
            items[key] = str(v)
    return items


def init(lang: str = "en") -> None:
    """Initialize the i18n system with a default language."""
    global _current_lang
    _current_lang = lang
    if lang not in _translations:
        _translations[lang] = load_language(lang)
    # Always load English as fallback
    if "en" not in _translations:
        _translations["en"] = load_language("en")


def set_language(lang: str) -> None:
    """Switch the active language."""
    global _current_lang
    if lang not in _translations:
        _translations[lang] = load_language(lang)
    _current_lang = lang


def get_language() -> str:
    """Return the current language code."""
    return _current_lang


def t(key: str, **kwargs: Any) -> str:
    """Translate a key. Falls back to English, then to the key itself.

    Usage:
        t("input.latitude")           -> "Latitude"
        t("status.pixels", n=42)      -> "42 pixels analyzed"
    """
    text = _translations.get(_current_lang, {}).get(key)
    if text is None:
        text = _translations.get("en", {}).get(key)
    if text is None:
        return key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
