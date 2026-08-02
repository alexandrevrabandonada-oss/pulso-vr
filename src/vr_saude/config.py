from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def project_root() -> Path:
    """Return the repository root from the installed source location."""
    return Path(__file__).resolve().parents[2]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"YAML must contain a mapping: {path}")
    return value


def load_config(name: str, root: Path | None = None) -> dict[str, Any]:
    base = root or project_root()
    return load_yaml(base / "config" / name)
