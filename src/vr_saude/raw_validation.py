from __future__ import annotations

import json
import csv
import gzip
import zipfile
from pathlib import Path
from typing import Any

from .provenance import sha256_file


SIM_REQUIRED_FIELDS = {"CODMUNRES", "SEXO", "IDADE", "CAUSABAS"}


def _sidecar_status(path: Path) -> tuple[bool, str]:
    sidecar = Path(f"{path}.sha256")
    if not sidecar.exists():
        return False, "missing_sha256_sidecar"
    declared = sidecar.read_text(encoding="utf-8").split()[0]
    actual = sha256_file(path)
    return declared == actual, actual


def validate_raw_file(path: Path) -> dict[str, Any]:
    ok_hash, digest_or_reason = _sidecar_status(path)
    result: dict[str, Any] = {
        "path": str(path),
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": digest_or_reason if ok_hash else "",
        "hash_ok": ok_hash,
        "format_ok": False,
        "format_details": {},
        "errors": [] if ok_hash else [digest_or_reason],
    }
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            result["format_ok"] = isinstance(payload, (list, dict))
            result["format_details"] = {"json_type": type(payload).__name__}
        elif suffix == ".geojson":
            raw = path.read_bytes()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            payload = json.loads(raw.decode("utf-8"))
            features = payload.get("features") if isinstance(payload, dict) else None
            result["format_ok"] = payload.get("type") == "FeatureCollection" and isinstance(features, list)
            result["format_details"] = {
                "json_type": type(payload).__name__,
                "geojson_type": payload.get("type") if isinstance(payload, dict) else None,
                "features": len(features) if isinstance(features, list) else 0,
            }
            if not result["format_ok"]:
                result["errors"].append("invalid_geojson_feature_collection")
        elif suffix == ".zip":
            with zipfile.ZipFile(path) as archive:
                bad_member = archive.testzip()
                result["format_ok"] = bad_member is None
                result["format_details"] = {
                    "members": len(archive.namelist()),
                    "first_members": archive.namelist()[:10],
                }
                if bad_member:
                    result["errors"].append(f"corrupt_zip_member:{bad_member}")
        elif suffix == ".csv":
            with path.open("rb") as handle:
                header_line = handle.readline().decode("latin1").strip()
            fields = {field.strip().strip('"') for field in next(csv.reader([header_line], delimiter=";"))}
            panel_csv = len(fields) == 2 and "Casos" in fields
            if panel_csv:
                result["format_ok"] = True
                result["format_details"] = {
                    "delimiter": ";",
                    "columns": len(fields),
                    "source_layout": "Painel-Oncologia TabNet two-column result",
                    "fields": sorted(fields),
                }
            else:
                missing = sorted(SIM_REQUIRED_FIELDS - fields)
                result["format_ok"] = not missing
                result["format_details"] = {
                    "delimiter": ";",
                    "columns": len(fields),
                    "required_fields_present": sorted(SIM_REQUIRED_FIELDS & fields),
                    "missing_required_fields": missing,
                }
                if missing:
                    result["errors"].append("missing_required_fields:" + ",".join(missing))
        elif suffix == ".pdf":
            header = path.read_bytes()[:5]
            result["format_ok"] = header == b"%PDF-"
            result["format_details"] = {"header": header.decode("ascii", errors="replace")}
        elif suffix in {".html", ".htm"}:
            text = path.read_text(encoding="latin1", errors="replace")
            markers = {
                "tabnet_title": "TabNet Win32" in text,
                "total_label": '"Total"' in text,
                "source_label": "Sistema de Informações Hospitalares" in text,
            }
            result["format_ok"] = all(markers.values())
            result["format_details"] = markers
            if not result["format_ok"]:
                result["errors"].append("unexpected_tabnet_html_markers")
        elif suffix == ".parquet":
            import pyarrow.parquet as pq

            metadata = pq.ParquetFile(path).metadata
            result["format_ok"] = metadata is not None and metadata.num_rows >= 0
            result["format_details"] = {
                "rows": metadata.num_rows,
                "columns": metadata.num_columns,
                "row_groups": metadata.num_row_groups,
            }
        else:
            result["errors"].append(f"unsupported_sample_format:{suffix}")
    except Exception as exc:  # pragma: no cover - source-specific parser failures
        result["errors"].append(f"{type(exc).__name__}:{exc}")
    result["ok"] = bool(result["hash_ok"] and result["format_ok"] and not result["errors"])
    return result


def validate_raw_samples(root: Path) -> list[dict[str, Any]]:
    raw = root / "data" / "raw"
    results = []
    for path in sorted(raw.iterdir()):
        if path.is_file() and path.name not in {"README.md", ".gitkeep"} and not path.name.endswith(".sha256"):
            results.append(validate_raw_file(path))
    return results


def write_raw_validation_report(root: Path) -> tuple[Path, Path, list[dict[str, Any]]]:
    results = validate_raw_samples(root)
    json_path = root / "reports" / "quality" / "raw_samples_validation.json"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path = root / "reports" / "quality" / "raw_samples_validation.md"
    lines = [
        "# Validação de amostras brutas",
        "",
        "Esta validação testa sidecar SHA-256 e integridade estrutural básica; "
        "não substitui a reconciliação epidemiológica com totais oficiais.",
        "",
        "| arquivo | bytes | hash | formato | status | detalhes |",
        "|---|---:|---|---|---|---|",
    ]
    for item in results:
        details = json.dumps(item["format_details"], ensure_ascii=False, sort_keys=True)
        lines.append(
            f"| {item['filename']} | {item['bytes']} | "
            f"{'OK' if item['hash_ok'] else 'FALHA'} | "
            f"{'OK' if item['format_ok'] else 'FALHA'} | "
            f"{'OK' if item['ok'] else 'FALHA'} | {details} |"
        )
    if not results:
        lines.append("| — | 0 | — | — | sem dados brutos | nenhuma amostra adquirida |")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, markdown_path, results
