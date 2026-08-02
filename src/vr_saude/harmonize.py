from __future__ import annotations

import json
import csv
import re
import zipfile
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .config import load_config
from .provenance import sha256_file, utc_now


SIM_REQUIRED = {"CODMUNRES", "SEXO", "IDADE", "CAUSABAS"}
SIVEP_REQUIRED = {"CO_MUN_RES", "CS_SEXO", "NU_IDADE_N", "DT_SIN_PRI", "CLASSI_FIN", "EVOLUCAO"}
SIM_OPTIONAL = {
    "CODMUNOCOR",
    "CAUSAMAT",
    "DTOBITO",
    "DTNASC",
    "TIPOBITO",
    "STDOEPIDEM",
}
SIVEP_OPTIONAL = {"CO_MUN_NOT", "CS_RACA", "CS_GESTANT", "DT_EVOLUCA", "DT_NOTIFIC", "TP_IDADE"}


def _vr_code(root: Path) -> str:
    config = load_config("territories.yml", root)
    return str(config["volta_redonda"]["datasus_code_6_expected"])


def _source_year(path: Path) -> int:
    match = re.search(r"(?<!\d)(20\d{2})(?!\d)", path.name)
    if not match:
        raise ValueError(f"cannot infer source year from {path.name}")
    return int(match.group(1))


def _string_series(frame: pd.DataFrame, field: str, length: int) -> pd.Series:
    if field not in frame.columns:
        return pd.Series([""] * length, dtype="string")
    values = frame[field].astype("string").fillna("").str.strip()
    return values.str.replace(r"\.0$", "", regex=True)


def _date_series(frame: pd.DataFrame, field: str, length: int, compact: bool = False) -> pd.Series:
    values = _string_series(frame, field, length)
    if compact:
        return pd.to_datetime(values, format="%d%m%Y", errors="coerce")
    return pd.to_datetime(frame[field], errors="coerce") if field in frame.columns else pd.Series(
        pd.NaT, index=frame.index, dtype="datetime64[ns]"
    )


def _base_metadata(
    frame: pd.DataFrame,
    root: Path,
    source: str,
    year: int,
    source_file: str,
    row_offset: int,
    vr_code: str,
) -> pd.DataFrame:
    length = len(frame)
    residence = _string_series(frame, "CODMUNRES" if source == "SIM" else "CO_MUN_RES", length)
    return pd.DataFrame(
        {
            "source": pd.Series([source] * length, dtype="string"),
            "source_year": pd.Series([year] * length, dtype="int16"),
            "source_file": pd.Series([source_file] * length, dtype="string"),
            "source_row_number": pd.Series(range(row_offset + 1, row_offset + length + 1), dtype="int64"),
            "municipality_code_datasus": residence,
            "residence_code_valid": residence.str.fullmatch(r"\d{6}").fillna(False),
            "residence_is_vr": residence.eq(vr_code),
        }
    )


def _write_batches(output: Path, batches: Iterable[pd.DataFrame]) -> tuple[int, int, list[str], dict[str, Any]]:
    writer: pq.ParquetWriter | None = None
    rows = 0
    vr_rows = 0
    columns: list[str] = []
    missing_counts: dict[str, int] = {}
    invalid_residence_rows = 0
    source_row_sequence_ok = True
    expected_source_row = 1
    date_parse_failures: dict[str, int] = {}
    try:
        for frame in batches:
            if frame.empty:
                continue
            table = pa.Table.from_pandas(frame, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(output, table.schema, compression="zstd")
                columns = list(frame.columns)
            elif table.schema != writer.schema:
                raise TypeError(f"inconsistent normalized schema while writing {output}")
            writer.write_table(table)
            rows += len(frame)
            vr_rows += int(frame["residence_is_vr"].sum())
            invalid_residence_rows += int((~frame["residence_code_valid"].fillna(False)).sum())
            source_rows = frame["source_row_number"].to_numpy()
            if len(source_rows) and (source_rows != range(expected_source_row, expected_source_row + len(source_rows))).any():
                source_row_sequence_ok = False
            expected_source_row += len(source_rows)
            for column in frame.columns:
                series = frame[column]
                missing = int(series.isna().sum())
                if pd.api.types.is_string_dtype(series.dtype):
                    missing += int(series.fillna("").eq("").sum())
                missing_counts[column] = missing_counts.get(column, 0) + missing
            for raw_column, parsed_column in (
                ("death_date_raw", "death_date"),
                ("birth_date_raw", "birth_date"),
            ):
                if raw_column in frame and parsed_column in frame:
                    raw_values = frame[raw_column].fillna("")
                    date_parse_failures[raw_column] = date_parse_failures.get(raw_column, 0) + int(
                        raw_values.ne("").sum() - frame.loc[raw_values.ne(""), parsed_column].notna().sum()
                    )
    finally:
        if writer is not None:
            writer.close()
    if writer is None:
        raise ValueError(f"no rows written to {output}")
    quality = {
        "missing_counts": missing_counts,
        "invalid_residence_rows": invalid_residence_rows,
        "source_row_sequence_ok": source_row_sequence_ok,
        "date_parse_failures": date_parse_failures,
    }
    return rows, vr_rows, columns, quality


def _sim_batches(path: Path, root: Path, vr_code: str, chunk_size: int) -> Iterable[pd.DataFrame]:
    year = _source_year(path)
    source_file = str(path.relative_to(root))
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"expected one SIM CSV member in {path.name}, found {len(members)}")
        with archive.open(members[0]) as handle:
            reader = pd.read_csv(
                handle,
                sep=";",
                encoding="latin1",
                dtype="string",
                chunksize=chunk_size,
                low_memory=False,
            )
            row_offset = 0
            for chunk in reader:
                chunk = chunk.reset_index(drop=True)
                missing = sorted(SIM_REQUIRED - set(chunk.columns))
                if missing:
                    raise ValueError(f"{path.name}: missing SIM fields {missing}")
                normalized = _base_metadata(chunk, root, "SIM", year, source_file, row_offset, vr_code)
                normalized["municipality_code_occurrence"] = _string_series(chunk, "CODMUNOCOR", len(chunk))
                normalized["sex_raw"] = _string_series(chunk, "SEXO", len(chunk))
                normalized["age_raw"] = _string_series(chunk, "IDADE", len(chunk))
                normalized["underlying_cause"] = _string_series(chunk, "CAUSABAS", len(chunk))
                normalized["multiple_cause_raw"] = _string_series(chunk, "CAUSAMAT", len(chunk))
                normalized["death_date_raw"] = _string_series(chunk, "DTOBITO", len(chunk))
                normalized["death_date"] = _date_series(chunk, "DTOBITO", len(chunk), compact=True)
                normalized["birth_date_raw"] = _string_series(chunk, "DTNASC", len(chunk))
                normalized["birth_date"] = _date_series(chunk, "DTNASC", len(chunk), compact=True)
                normalized["death_type_raw"] = _string_series(chunk, "TIPOBITO", len(chunk))
                normalized["status_raw"] = _string_series(chunk, "STDOEPIDEM", len(chunk))
                row_offset += len(chunk)
                yield normalized


def _sivep_batches(path: Path, root: Path, vr_code: str, batch_size: int) -> Iterable[pd.DataFrame]:
    year = _source_year(path)
    source_file = str(path.relative_to(root))
    parquet = pq.ParquetFile(path)
    fields = set(parquet.schema_arrow.names)
    missing = sorted(SIVEP_REQUIRED - fields)
    if missing:
        raise ValueError(f"{path.name}: missing SIVEP fields {missing}")
    selected = sorted(
        SIVEP_REQUIRED
        | {
            "CO_MUN_NOT",
            "CS_RACA",
            "CS_GESTANT",
            "DT_EVOLUCA",
            "DT_NOTIFIC",
            "TP_IDADE",
        }
        & fields
    )
    row_offset = 0
    for batch in parquet.iter_batches(columns=selected, batch_size=batch_size):
        chunk = batch.to_pandas()
        normalized = _base_metadata(chunk, root, "SIVEP-SRAG", year, source_file, row_offset, vr_code)
        normalized["municipality_code_notification"] = _string_series(chunk, "CO_MUN_NOT", len(chunk))
        normalized["sex_raw"] = _string_series(chunk, "CS_SEXO", len(chunk))
        normalized["age_raw"] = _string_series(chunk, "NU_IDADE_N", len(chunk))
        normalized["age_unit_raw"] = _string_series(chunk, "TP_IDADE", len(chunk))
        normalized["symptom_onset_date"] = _date_series(chunk, "DT_SIN_PRI", len(chunk))
        normalized["notification_date"] = _date_series(chunk, "DT_NOTIFIC", len(chunk))
        normalized["outcome_date"] = _date_series(chunk, "DT_EVOLUCA", len(chunk))
        normalized["final_classification_raw"] = _string_series(chunk, "CLASSI_FIN", len(chunk))
        normalized["outcome_raw"] = _string_series(chunk, "EVOLUCAO", len(chunk))
        normalized["race_raw"] = _string_series(chunk, "CS_RACA", len(chunk))
        normalized["gestation_raw"] = _string_series(chunk, "CS_GESTANT", len(chunk))
        row_offset += len(chunk)
        yield normalized


def harmonize_file(root: Path, path: Path, chunk_size: int = 100_000) -> dict[str, Any]:
    if path.suffix.lower() == ".zip":
        source = "SIM"
        output_name = f"sim_{_source_year(path)}_harmonized.parquet"
        batches = _sim_batches(path, root, _vr_code(root), chunk_size)
        with zipfile.ZipFile(path) as archive:
            member = next(name for name in archive.namelist() if name.lower().endswith(".csv"))
            with archive.open(member) as handle:
                input_fields = next(csv.reader((line.decode("latin1") for line in handle), delimiter=";"))
        optional_fields = SIM_OPTIONAL
    elif path.suffix.lower() == ".parquet" and path.name.startswith("sivep_"):
        source = "SIVEP-SRAG"
        output_name = f"sivep_{_source_year(path)}_harmonized.parquet"
        batches = _sivep_batches(path, root, _vr_code(root), chunk_size)
        input_fields = pq.ParquetFile(path).schema_arrow.names
        optional_fields = SIVEP_OPTIONAL
    else:
        raise ValueError(f"unsupported harmonization input: {path.name}")
    output = root / "data" / "interim" / output_name
    output.parent.mkdir(parents=True, exist_ok=True)
    rows, vr_rows, columns, quality = _write_batches(output, batches)
    return {
        "source": source,
        "source_year": _source_year(path),
        "input_path": str(path.relative_to(root)),
        "input_sha256": sha256_file(path),
        "input_fields": sorted(input_fields),
        "optional_fields_absent": sorted(optional_fields - set(input_fields)),
        "output_path": str(output.relative_to(root)),
        "output_sha256": sha256_file(output),
        "rows": rows,
        "residence_vr_rows": vr_rows,
        "columns": columns,
        "quality": quality,
        "status": "harmonized_interim_only",
    }


def harmonize_sources(root: Path, source: str = "all", chunk_size: int = 100_000) -> tuple[Path, list[dict[str, Any]]]:
    paths: list[Path] = []
    if source in {"all", "sim"}:
        paths.extend(sorted((root / "data" / "raw").glob("sim_*.zip")))
    if source in {"all", "sivep"}:
        paths.extend(sorted((root / "data" / "raw").glob("sivep_*.parquet")))
    if source not in {"all", "sim", "sivep"}:
        raise ValueError(f"unknown harmonization source: {source}")
    results = [harmonize_file(root, path, chunk_size) for path in paths]
    manifest = {
        "generated_at": utc_now(),
        "status": "interim_harmonization_no_epidemiological_estimate",
        "source_filter": source,
        "results": results,
        "rules": [
            "Residence uses CODMUNRES for SIM and CO_MUN_RES for SIVEP-SRAG.",
            "Occurrence and notification municipality fields remain separate.",
            "Raw files are never edited or overwritten.",
            "Normalized outputs are interim artifacts and are not final analytical data.",
        ],
    }
    destination = root / "reports" / "quality" / "harmonization_manifest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination, results
