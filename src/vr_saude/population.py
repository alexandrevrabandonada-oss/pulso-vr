from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import load_config
from .download import download_public_file
from .provenance import sha256_file


ESTIMATE_URL_TEMPLATE = "https://apisidra.ibge.gov.br/values/t/6579/n6/all/p/{year}/v/9324"
CENSUS_URL = "https://apisidra.ibge.gov.br/values/t/9514/n6/all/p/2022/v/93"
RJ_MUNICIPALITY_COUNT = 92


def requested_years(start_year: int, end_year: int) -> list[int]:
    if start_year > end_year:
        raise ValueError("start year must not be after end year")
    if end_year - start_year > 30:
        raise ValueError("a population acquisition is limited to 31 years")
    return list(range(start_year, end_year + 1))


def raw_filename(year: int) -> str:
    if year == 2022:
        return "ibge_sidra_9514_population_2022.json"
    return f"ibge_sidra_6579_population_{year}.json"


def raw_url(year: int) -> str:
    return CENSUS_URL if year == 2022 else ESTIMATE_URL_TEMPLATE.format(year=year)


def acquire_population(
    root: Path,
    start_year: int,
    end_year: int,
) -> list[Path]:
    paths: list[Path] = []
    for year in requested_years(start_year, end_year):
        paths.append(
            download_public_file(
                root,
                source_id=("ibge_sidra_9514_population_2022" if year == 2022 else f"ibge_sidra_6579_population_{year}"),
                url=raw_url(year),
                filename=raw_filename(year),
                period=str(year),
                territory="Brasil; filtro RJ na harmonização",
            )
        )
    return paths


def _read_sidra_payload(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"SIDRA payload is not a non-empty list: {path}")
    rows = payload[1:]
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    required = {"D1C", "D1N", "D2C", "V"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"SIDRA payload missing fields {sorted(missing)}: {path}")
    frame["municipality_code_ibge"] = frame["D1C"].astype(str).str.zfill(7)
    frame["municipality_name"] = frame["D1N"].astype(str)
    frame["year"] = pd.to_numeric(frame["D2C"], errors="coerce").astype("Int64")
    frame["population"] = pd.to_numeric(frame["V"], errors="coerce")
    frame = frame.loc[frame["population"].notna()].copy()
    frame["population"] = frame["population"].astype("int64")
    return frame


def _population_source(path: Path) -> tuple[str, str]:
    if "9514" in path.name:
        return "9514", "census_2022"
    return "6579", "annual_estimate"


def _municipality_frame(root: Path, years: list[int]) -> tuple[pd.DataFrame, dict[str, object]]:
    records: list[pd.DataFrame] = []
    source_by_year: dict[str, str] = {}
    missing_payload_years: list[int] = []
    input_files: list[dict[str, object]] = []
    for year in years:
        path = root / "data" / "raw" / raw_filename(year)
        if not path.exists():
            raise FileNotFoundError(f"population raw file is missing: {path}")
        table, source_status = _population_source(path)
        frame = _read_sidra_payload(path)
        if frame.empty:
            missing_payload_years.append(year)
            continue
        frame = frame.loc[frame["municipality_code_ibge"].str.startswith("33")].copy()
        if frame.empty:
            missing_payload_years.append(year)
            continue
        frame["source_table"] = table
        frame["source_status"] = source_status
        frame["source_file"] = str(path.relative_to(root))
        frame["source_sha256"] = sha256_file(path)
        frame = frame[
            [
                "year",
                "municipality_code_ibge",
                "municipality_name",
                "population",
                "source_table",
                "source_status",
                "source_file",
                "source_sha256",
            ]
        ]
        records.append(frame)
        source_by_year[str(year)] = source_status
        input_files.append(
            {
                "year": year,
                "path": str(path.relative_to(root)),
                "sha256": sha256_file(path),
                "rows_in_rj": len(frame),
            }
        )
    if records:
        municipality = pd.concat(records, ignore_index=True)
    else:
        municipality = pd.DataFrame(
            columns=[
                "year",
                "municipality_code_ibge",
                "municipality_name",
                "population",
                "source_table",
                "source_status",
                "source_file",
                "source_sha256",
            ]
        )
    municipality["year"] = pd.to_numeric(municipality["year"], errors="coerce").astype("Int64")
    municipality["municipality_code_ibge"] = municipality["municipality_code_ibge"].astype(str)
    duplicate_keys = municipality.duplicated(["year", "municipality_code_ibge"]).sum()
    invalid_codes = municipality.loc[
        ~municipality["municipality_code_ibge"].str.match(r"^33\d{5}$"), "municipality_code_ibge"
    ].tolist()
    metadata = {
        "source_by_year": source_by_year,
        "missing_payload_years": missing_payload_years,
        "input_files": input_files,
        "duplicate_keys": int(duplicate_keys),
        "invalid_codes": invalid_codes,
    }
    return municipality, metadata


def _denominator_frame(root: Path, municipality: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    territories = load_config("territories.yml", root)
    vr_code = str(territories["volta_redonda"]["ibge_code_7"])
    rows: list[dict[str, object]] = []
    counts: dict[str, int] = {}
    missing_vr_years: list[int] = []
    incomplete_years: list[int] = []
    for year, frame in municipality.groupby("year", dropna=True):
        year_int = int(year)
        counts[str(year_int)] = int(frame["municipality_code_ibge"].nunique())
        total = int(frame["population"].sum())
        vr = frame.loc[frame["municipality_code_ibge"] == vr_code, "population"]
        if vr.empty:
            missing_vr_years.append(year_int)
            continue
        if counts[str(year_int)] != RJ_MUNICIPALITY_COUNT:
            incomplete_years.append(year_int)
        vr_value = int(vr.iloc[0])
        source_file = ";".join(sorted(frame["source_file"].unique()))
        source_sha256 = ";".join(sorted(frame["source_sha256"].unique()))
        source_status = ";".join(sorted(frame["source_status"].unique()))
        for geography, value in [
            ("rj_total", total),
            ("volta_redonda", vr_value),
            ("rest_of_rj_excluding_vr", total - vr_value),
        ]:
            rows.append(
                {
                    "year": year_int,
                    "geography": geography,
                    "municipality_code_ibge_vr": vr_code,
                    "population": value,
                    "unit": "pessoas",
                    "source_status": source_status,
                    "source_files": source_file,
                    "source_sha256s": source_sha256,
                }
            )
    denominator = pd.DataFrame(rows)
    if not denominator.empty:
        denominator = denominator.sort_values(["year", "geography"]).reset_index(drop=True)
    metadata = {
        "municipality_count_by_year": counts,
        "missing_vr_years": sorted(missing_vr_years),
        "incomplete_years": sorted(incomplete_years),
    }
    return denominator, metadata


def _write_report(root: Path, years: list[int], municipality: pd.DataFrame, denominator: pd.DataFrame, manifest: dict[str, object]) -> Path:
    report = root / "reports" / "technical" / "denominadores.md"
    available = sorted(denominator["year"].unique().tolist()) if not denominator.empty else []
    missing = [year for year in years if year not in available]
    rows = []
    for row in denominator.itertuples(index=False):
        rows.append([row.year, row.geography, row.population, row.source_status])
    lines = [
        "# Denominadores populacionais",
        "",
        f"Execução: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "## Regra",
        "",
        "A população anual é obtida da SIDRA. A tabela 6579 é usada para estimativas "
        "anuais; 2022 usa a população residente observada no Censo da tabela 9514. "
        "A soma do RJ é feita a partir dos municípios cujo código IBGE começa por 33, "
        "e o comparador é essa soma menos Volta Redonda.",
        "",
        f"- Anos solicitados: **{years[0]}–{years[-1]}**.",
        f"- Anos disponíveis: **{', '.join(str(year) for year in available) if available else 'nenhum'}**.",
        f"- Anos ausentes, sem interpolação: **{', '.join(str(year) for year in missing) if missing else 'nenhum'}**.",
        f"- Linhas municipais RJ: **{len(municipality)}**.",
        "",
        "## Denominadores agregados",
        "",
        "| ano | território | população | origem |",
        "|---:|---|---:|---|",
    ]
    lines.extend(f"| {year} | {geography} | {population} | {status} |" for year, geography, population, status in rows)
    lines.extend(
        [
            "",
            "## Controle de qualidade",
            "",
            f"- Municípios esperados no RJ por ano: **{RJ_MUNICIPALITY_COUNT}**.",
            f"- Anos com quantidade municipal incompleta: **{manifest['denominator']['incomplete_years'] or 'nenhum'}**.",
            f"- Anos sem VR: **{manifest['denominator']['missing_vr_years'] or 'nenhum'}**.",
            f"- Chaves municipais duplicadas: **{manifest['municipality']['duplicate_keys']}**.",
            "",
            "Esses denominadores permitem taxas brutas agregadas. Denominadores por idade/sexo "
            "foram harmonizados separadamente para 2022; ainda não há uma série completa "
            "compatível para padronização temporal.",
            "",
            "2026 não é tratado como zero: não há estimativa anual correspondente no arquivo adquirido.",
        ]
    )
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def harmonize_population(root: Path, start_year: int, end_year: int) -> tuple[Path, Path, Path]:
    years = requested_years(start_year, end_year)
    municipality, municipality_metadata = _municipality_frame(root, years)
    denominator, denominator_metadata = _denominator_frame(root, municipality)
    processed = root / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    municipality_path = processed / "population_rj_municipality.parquet"
    denominator_path = processed / "population_denominators.parquet"
    municipality.to_parquet(municipality_path, index=False)
    denominator.to_parquet(denominator_path, index=False)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "validated_denominators_no_rates",
        "requested_years": years,
        "available_years": sorted(denominator["year"].unique().tolist()) if not denominator.empty else [],
        "missing_years": [
            year
            for year in years
            if denominator.empty or year not in set(denominator["year"].unique().tolist())
        ],
        "municipality": {
            **municipality_metadata,
            "rows": int(len(municipality)),
            "path": str(municipality_path.relative_to(root)),
            "sha256": sha256_file(municipality_path),
        },
        "denominator": {
            **denominator_metadata,
            "rows": int(len(denominator)),
            "path": str(denominator_path.relative_to(root)),
            "sha256": sha256_file(denominator_path),
        },
        "notes": [
            "2022 is sourced from SIDRA table 9514 Censo population resident, total sex and total age.",
            "Other requested years use SIDRA table 6579 resident population estimates when available.",
            "Missing years are explicit and are not interpolated or replaced by zero.",
            "The rest-of-RJ comparator excludes IBGE code 3306305 by construction.",
            "No age-specific denominator or epidemiological rate is produced by this step.",
        ],
    }
    manifest_path = root / "reports" / "quality" / "population_denominator_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = _write_report(root, years, municipality, denominator, manifest)
    return municipality_path, denominator_path, report_path
