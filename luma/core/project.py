"""Versioned project files for reproducible LUMA analyses."""

from __future__ import annotations

import json
from pathlib import Path
from collections.abc import Mapping

from luma.output.serialization import serializable_parameters

PROJECT_FORMAT = "luma-project"
PROJECT_VERSION = 1


def build_project(
    parameters: Mapping[str, object], *, source_key: str | None,
    source_year: int | None, legend_key: str | None,
) -> dict:
    """Build a stable, JSON-safe project payload."""
    return {
        "format": PROJECT_FORMAT,
        "version": PROJECT_VERSION,
        "parameters": serializable_parameters(parameters),
        "source": {
            "key": source_key,
            "year": source_year,
            "legend": legend_key,
        },
    }


def save_project(path: str | Path, payload: Mapping[str, object]) -> None:
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_project(path: str | Path) -> dict:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Não foi possível abrir o projeto: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("format") != PROJECT_FORMAT:
        raise ValueError("Arquivo não é um projeto LUMA válido.")
    if payload.get("version") != PROJECT_VERSION:
        raise ValueError(
            f"Versão de projeto não suportada: {payload.get('version')}."
        )
    if not isinstance(payload.get("parameters"), dict) or not isinstance(payload.get("source"), dict):
        raise ValueError("Projeto LUMA sem parâmetros ou fonte válidos.")
    return payload
