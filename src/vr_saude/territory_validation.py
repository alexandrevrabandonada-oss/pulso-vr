from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

import pyarrow.parquet as pq

from .config import load_config


def _code(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().lstrip("0") or "0"


def _expected_codes(root: Path) -> tuple[str, str]:
    territories = load_config("territories.yml", root)
    volta_redonda = territories["volta_redonda"]
    return (
        str(volta_redonda["datasus_code_6_expected"]),
        str(volta_redonda["ibge_code_7"]),
    )


def _sim_result(path: Path, expected_code: str) -> dict[str, object]:
    result: dict[str, object] = {
        "path": str(path),
        "source": "SIM",
        "field": "CODMUNRES",
        "format": "ZIP/CSV",
        "ok": False,
        "rows": 0,
        "target_code": expected_code,
        "target_rows": 0,
        "observed_code_lengths": {},
        "errors": [],
    }
    try:
        with ZipFile(path) as archive:
            members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if len(members) != 1:
                result["errors"] = [f"expected one CSV member, found {len(members)}"]
                return result
            with archive.open(members[0]) as raw:
                reader = csv.DictReader((line.decode("latin1") for line in raw), delimiter=";")
                if "CODMUNRES" not in (reader.fieldnames or []):
                    result["errors"] = ["CODMUNRES not found in CSV header"]
                    return result
                lengths: Counter[str] = Counter()
                for row in reader:
                    value = _code(row.get("CODMUNRES"))
                    result["rows"] = int(result["rows"]) + 1
                    lengths[str(len(value))] += 1
                    if value == expected_code:
                        result["target_rows"] = int(result["target_rows"]) + 1
                result["observed_code_lengths"] = dict(sorted(lengths.items()))
    except Exception as exc:  # pragma: no cover - exercised by corrupt input
        result["errors"] = [f"{type(exc).__name__}: {exc}"]
        return result
    if int(result["target_rows"]) == 0:
        result["errors"] = [f"target code {expected_code} not observed"]
        return result
    result["ok"] = True
    return result


def _sivep_result(path: Path, expected_code: str) -> dict[str, object]:
    result: dict[str, object] = {
        "path": str(path),
        "source": "SIVEP-SRAG",
        "field": "CO_MUN_RES",
        "format": "Parquet",
        "ok": False,
        "rows": 0,
        "target_code": expected_code,
        "target_rows": 0,
        "observed_code_lengths": {},
        "errors": [],
    }
    try:
        parquet = pq.ParquetFile(path)
        if "CO_MUN_RES" not in parquet.schema_arrow.names:
            result["errors"] = ["CO_MUN_RES not found in Parquet schema"]
            return result
        lengths: Counter[str] = Counter()
        for batch in parquet.iter_batches(columns=["CO_MUN_RES"], batch_size=100_000):
            for raw_value in batch.column(0).to_pylist():
                value = _code(raw_value)
                result["rows"] = int(result["rows"]) + 1
                lengths[str(len(value))] += 1
                if value == expected_code:
                    result["target_rows"] = int(result["target_rows"]) + 1
        result["observed_code_lengths"] = dict(sorted(lengths.items()))
    except Exception as exc:  # pragma: no cover - exercised by corrupt input
        result["errors"] = [f"{type(exc).__name__}: {exc}"]
        return result
    if int(result["target_rows"]) == 0:
        result["errors"] = [f"target code {expected_code} not observed"]
        return result
    result["ok"] = True
    return result


def validate_territory_samples(root: Path) -> list[dict[str, object]]:
    expected_code, _ibge_code = _expected_codes(root)
    results: list[dict[str, object]] = []
    for path in sorted((root / "data" / "raw").glob("sim_*.zip")):
        results.append(_sim_result(path, expected_code))
    for path in sorted((root / "data" / "raw").glob("sivep_*.parquet")):
        results.append(_sivep_result(path, expected_code))
    return results


def write_territory_report(root: Path) -> tuple[Path, Path, list[dict[str, object]]]:
    results = validate_territory_samples(root)
    for item in results:
        try:
            item["path"] = str(Path(str(item["path"])).resolve().relative_to(root.resolve()))
        except ValueError:
            pass
    json_path = root / "reports" / "quality" / "territory_code_validation.json"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    expected_code, ibge_code = _expected_codes(root)
    lines = [
        "# Validação dos códigos territoriais",
        "",
        "Esta checagem confirma que os filtros de residência encontram Volta Redonda nos arquivos brutos.",
        "",
        f"- Código DATASUS esperado no campo de residência: `{expected_code}`.",
        f"- Código IBGE de referência cadastral: `{ibge_code}`.",
        "- O código observado nos campos SIM `CODMUNRES` e SIVEP `CO_MUN_RES` é o código DATASUS de seis dígitos.",
        "",
        "| Arquivo | Fonte/campo | Linhas | Linhas VR | Tamanhos observados | Status |",
        "|---|---|---:|---:|---|---|",
    ]
    for item in results:
        path = Path(str(item["path"])).name
        lengths = json.dumps(item["observed_code_lengths"], ensure_ascii=False, sort_keys=True)
        status = "OK" if item["ok"] else "FALHA: " + "; ".join(item["errors"])
        lines.append(
            f"| `{path}` | {item['source']} / `{item['field']}` | {item['rows']} | "
            f"{item['target_rows']} | `{lengths}` | {status} |"
        )
    md_path = root / "reports" / "quality" / "territory_code_validation.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, results
