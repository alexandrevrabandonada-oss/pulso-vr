from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .config import load_config, project_root


REQUIRED_DIRS = [
    "config",
    "data/raw",
    "data/interim",
    "data/processed",
    "metadata",
    "src/vr_saude",
    "notebooks",
    "tests",
    "outputs",
    "reports/protocol",
    "reports/quality",
    "reports/technical",
    "reports/executive",
    "requests/lai",
    "requests/ethics",
    "requests/partnerships",
]
REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    "pyproject.toml",
    "Makefile",
    "config/outcomes.yml",
    "config/periods.yml",
    "config/sources.yml",
    "config/territories.yml",
    "metadata/source_catalog.csv",
    "metadata/extraction_log.csv",
    "reports/protocol/protocolo.md",
    "reports/protocol/matriz_perguntas.csv",
]
SOURCE_FIELDS = {
    "source_id",
    "domain",
    "title",
    "institution",
    "landing_url",
    "resource_url",
    "format",
    "geography",
    "temporal_coverage",
    "accessed_at",
    "version_or_update",
    "status",
    "planned_use",
    "limitations",
}


def _missing_paths(root: Path, paths: Iterable[str], kind: str) -> list[str]:
    issues: list[str] = []
    for value in paths:
        path = root / value
        if not path.is_dir() if kind == "directory" else not path.is_file():
            issues.append(f"missing {kind}: {value}")
    return issues


def validate_project(root: Path | None = None) -> list[str]:
    root = root or project_root()
    issues = _missing_paths(root, REQUIRED_DIRS, "directory")
    issues.extend(_missing_paths(root, REQUIRED_FILES, "file"))
    if issues:
        return issues

    try:
        outcomes = load_config("outcomes.yml", root)
        periods = load_config("periods.yml", root)
        sources = load_config("sources.yml", root)
        territories = load_config("territories.yml", root)
    except Exception as exc:  # pragma: no cover - message is user-facing
        return [f"configuration load failed: {exc}"]

    if not all(outcomes.get(section) for section in ("respiratory", "cardiovascular", "cardiorespiratory", "cancer")):
        issues.append("outcomes.yml must define respiratory, cardiovascular, cardiorespiratory and cancer outcomes")
    if periods.get("breaks", {}).get("respiratory_pandemic_start") != "2020-03":
        issues.append("periods.yml must define respiratory break at 2020-03")
    if periods.get("breaks", {}).get("oncology_line_start") != "2022-03":
        issues.append("periods.yml must define oncology line start at 2022-03")
    vr = territories.get("volta_redonda", {})
    if vr.get("ibge_code_7") != "3306305":
        issues.append("territories.yml must define Volta Redonda IBGE code 3306305")
    primary_rule = territories.get("comparators", {}).get("primary", {}).get("rule", "")
    if "selected municipality" not in primary_rule.lower() or "denominator" not in primary_rule.lower():
        issues.append("primary comparator must exclude the selected municipality from numerator and denominator")
    if sources.get("sources", {}).get("sih", {}).get("primary", {}).get("territory") != "residence in RJ":
        issues.append("SIH source must declare residence in RJ")

    catalog_path = root / "metadata" / "source_catalog.csv"
    with catalog_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing_fields = SOURCE_FIELDS - fields
        if missing_fields:
            issues.append(f"source catalog missing columns: {sorted(missing_fields)}")
        rows = list(reader)
    source_ids = [row.get("source_id", "") for row in rows]
    if len(source_ids) != len(set(source_ids)):
        issues.append("source catalog contains duplicate source_id values")
    if not any(row.get("status") == "verified" for row in rows):
        issues.append("source catalog must contain at least one verified source")

    for path in (root / "data" / "raw").iterdir():
        if path.is_file() and path.name not in {"README.md", ".gitkeep"} and not path.name.endswith(".sha256"):
            sidecar = Path(f"{path}.sha256")
            if not sidecar.exists():
                issues.append(f"raw file without SHA-256 sidecar: {path.relative_to(root)}")

    return issues
