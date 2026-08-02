from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path
from typing import Any


SIM_REQUIRED_FIELDS = {"CODMUNRES", "SEXO", "IDADE", "CAUSABAS"}
SIVEP_REQUIRED_FIELDS = {"CO_MUN_RES", "CS_SEXO", "NU_IDADE_N", "DT_SIN_PRI", "CLASSI_FIN", "EVOLUCAO"}


def inspect_sim_archive(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "source": "SIM",
        "format": "ZIP",
        "members": [],
        "ok": False,
        "errors": [],
    }
    try:
        with zipfile.ZipFile(path) as archive:
            for member in archive.namelist():
                if not member.lower().endswith(".csv"):
                    continue
                with archive.open(member) as handle:
                    header_line = handle.readline().decode("latin1").strip()
                fields = {field.strip().strip('"') for field in next(csv.reader([header_line], delimiter=";"))}
                missing = sorted(SIM_REQUIRED_FIELDS - fields)
                result["members"].append(
                    {
                        "member": member,
                        "delimiter": ";",
                        "columns": len(fields),
                        "required_fields_present": sorted(SIM_REQUIRED_FIELDS & fields),
                        "missing_required_fields": missing,
                    }
                )
                if missing:
                    result["errors"].append(f"{member}:missing:{','.join(missing)}")
            if not result["members"]:
                result["errors"].append("no_csv_member")
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}:{exc}")
    result["ok"] = not result["errors"]
    return result


def inspect_sivep_parquet(path: Path) -> dict[str, Any]:
    import pyarrow.parquet as pq

    result: dict[str, Any] = {
        "path": str(path),
        "source": "SIVEP",
        "format": "PARQUET",
        "ok": False,
        "errors": [],
    }
    try:
        parquet = pq.ParquetFile(path)
        fields = set(parquet.schema.names)
        missing = sorted(SIVEP_REQUIRED_FIELDS - fields)
        result.update(
            {
                "rows": parquet.metadata.num_rows,
                "columns": parquet.metadata.num_columns,
                "required_fields_present": sorted(SIVEP_REQUIRED_FIELDS & fields),
                "missing_required_fields": missing,
            }
        )
        if missing:
            result["errors"].append("missing:" + ",".join(missing))
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}:{exc}")
    result["ok"] = not result["errors"]
    return result


def validate_known_layouts(root: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    raw = root / "data" / "raw"
    for path in sorted(raw.glob("sim_*.zip")):
        results.append(inspect_sim_archive(path))
    for path in sorted(raw.glob("sivep_*.parquet")):
        results.append(inspect_sivep_parquet(path))
    return results


def write_layout_manifest(root: Path) -> tuple[Path, list[dict[str, Any]]]:
    results = validate_known_layouts(root)
    for item in results:
        try:
            item["path"] = str(Path(str(item["path"])).resolve().relative_to(root.resolve()))
        except ValueError:
            pass
    destination = root / "metadata" / "layout_manifest.json"
    destination.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination, results
