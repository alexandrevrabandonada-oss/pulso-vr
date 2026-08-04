
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import load_config
from .download import download_public_file
from .provenance import sha256_file


TABLE_ID = "9514"
YEAR = 2022
VARIABLE_ID = "93"
SEX_CODES = {"4": "masculino", "5": "feminino"}
AGE_GROUPS = ["<1", "1-4", "5-14", "15-24", "25-44", "45-64", "65-74", "75+"]
AGE_CODE_TO_GROUP = {
    "6557": "<1",
    "6558": "1-4",
    "6559": "1-4",
    "6560": "1-4",
    "6561": "1-4",
    "93084": "5-14",
    "93085": "5-14",
    "93086": "15-24",
    "93087": "15-24",
    "93088": "25-44",
    "93089": "25-44",
    "93090": "25-44",
    "93091": "25-44",
    "93092": "45-64",
    "93093": "45-64",
    "93094": "45-64",
    "93095": "45-64",
    "93096": "65-74",
    "93097": "65-74",
    "93098": "75+",
    "49108": "75+",
    "49109": "75+",
    "60040": "75+",
    "60041": "75+",
    "6653": "75+",
}
AGE_CATEGORY_CODES = list(AGE_CODE_TO_GROUP)
API_ROOT = "https://apisidra.ibge.gov.br/values/t/9514"
BRAZIL_STANDARD_RAW = "ibge_sidra_9514_age_sex_brazil_2022.json"


def _municipality_codes(root: Path) -> list[str]:
    path = root / "data" / "processed" / "population_rj_municipality.parquet"
    if not path.exists():
        raise FileNotFoundError(f"municipality population Parquet is missing: {path}")
    frame = pd.read_parquet(path)
    codes = sorted(
        frame.loc[
            (frame["year"] == YEAR) & frame["municipality_code_ibge"].astype(str).str.startswith("33"),
            "municipality_code_ibge",
        ]
        .astype(str)
        .unique()
        .tolist()
    )
    if len(codes) != 92:
        raise ValueError(f"expected 92 RJ municipalities for {YEAR}, found {len(codes)}")
    return codes


def _query_url(codes: list[str]) -> str:
    locality = ",".join(codes)
    sexes = "4,5"
    ages = ",".join(AGE_CATEGORY_CODES)
    return (
        f"{API_ROOT}/n6/{locality}/p/{YEAR}/v/{VARIABLE_ID}"
        f"/c2/{sexes}/c286/113635/c287/{ages}"
    )


def _brazil_query_url() -> str:
    sexes = "4,5"
    ages = ",".join(AGE_CATEGORY_CODES)
    return f"{API_ROOT}/n1/1/p/{YEAR}/v/{VARIABLE_ID}/c2/{sexes}/c286/113635/c287/{ages}"


def acquire_brazil_age_sex_population(root: Path) -> Path:
    """Acquire the Brazil 2022 age-sex standard used for direct standardization."""
    return download_public_file(
        root,
        source_id="ibge_sidra_9514_age_sex_brazil_2022",
        url=_brazil_query_url(),
        filename=BRAZIL_STANDARD_RAW,
        period=str(YEAR),
        territory="Brasil",
    )


def harmonize_brazil_age_sex_population(root: Path) -> Path:
    raw_path = root / "data" / "raw" / BRAZIL_STANDARD_RAW
    if not raw_path.exists():
        raise FileNotFoundError(f"Brazil age-sex raw payload is missing: {raw_path}")
    frame = _read_payload(raw_path, root)
    expected = len(AGE_GROUPS) * len(SEX_CODES)
    if len(frame) != expected or frame[["age_group", "sex"]].duplicated().any():
        raise ValueError(f"Brazil age-sex standard must contain {expected} unique cells")
    output = root / "data" / "processed" / "population_age_sex_brazil_2022.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "validated_census_2022_brazil_age_sex_standard",
        "year": YEAR,
        "rows": int(len(frame)),
        "population": int(frame["population"].sum()),
        "output_path": str(output.relative_to(root)),
        "output_sha256": sha256_file(output),
        "input_file": {"path": str(raw_path.relative_to(root)), "sha256": sha256_file(raw_path)},
    }
    manifest_path = root / "reports" / "quality" / "population_age_sex_brazil_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def acquire_age_sex_population(
    root: Path,
    chunk_size: int = 20,
) -> list[Path]:
    if chunk_size < 1 or chunk_size > 50:
        raise ValueError("chunk_size must be between 1 and 50")
    codes = _municipality_codes(root)
    paths: list[Path] = []
    for index in range(0, len(codes), chunk_size):
        chunk_number = index // chunk_size + 1
        chunk = codes[index : index + chunk_size]
        filename = f"ibge_sidra_9514_age_sex_{YEAR}_rj_{chunk_number:02d}.json"
        paths.append(
            download_public_file(
                root,
                source_id=f"ibge_sidra_9514_age_sex_{YEAR}_chunk_{chunk_number:02d}",
                url=_query_url(chunk),
                filename=filename,
                period=str(YEAR),
                territory=f"RJ; municípios {chunk[0]}–{chunk[-1]}",
            )
        )
    return paths


def _read_payload(path: Path, root: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError(f"SIDRA age-sex payload is empty: {path}")
    frame = pd.DataFrame(payload[1:])
    required = {"D1C", "D1N", "D2C", "D3C", "D4C", "D5C", "D6C", "V"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{path.name}: missing SIDRA fields {missing}")
    frame = frame.loc[
        (frame["D2C"].astype(str) == str(YEAR))
        & (frame["D3C"].astype(str) == VARIABLE_ID)
        & (frame["D5C"].astype(str) == "113635")
        & frame["D4C"].astype(str).isin(SEX_CODES)
        & frame["D6C"].astype(str).isin(AGE_CODE_TO_GROUP)
    ].copy()
    frame["municipality_code_ibge"] = frame["D1C"].astype(str).str.zfill(7)
    frame["municipality_name"] = frame["D1N"].astype(str)
    frame["sex"] = frame["D4C"].astype(str).map(SEX_CODES)
    frame["age_group"] = frame["D6C"].astype(str).map(AGE_CODE_TO_GROUP)
    zero_markers = frame["V"].astype(str).eq("-")
    frame["population"] = pd.to_numeric(frame["V"].where(~zero_markers, "0"), errors="coerce")
    if frame["population"].isna().any() or (frame["population"] < 0).any():
        raise ValueError(f"{path.name}: invalid population values")
    frame["population"] = frame["population"].astype(int)
    frame["sidra_zero_marker_count"] = zero_markers.astype("int8")
    frame["source_file"] = str(path.relative_to(root))
    frame["source_sha256"] = sha256_file(path)
    grouped = (
        frame.groupby(
            ["municipality_code_ibge", "municipality_name", "sex", "age_group"],
            as_index=False,
        )
        .agg(
            population=("population", "sum"),
            sidra_zero_marker_count=("sidra_zero_marker_count", "sum"),
            source_file=("source_file", "first"),
            source_sha256=("source_sha256", "first"),
        )
    )
    return grouped[
        [
            "municipality_code_ibge",
            "municipality_name",
            "sex",
            "age_group",
            "population",
            "sidra_zero_marker_count",
            "source_file",
            "source_sha256",
        ]
    ]


def _aggregate_denominators(root: Path, municipality: pd.DataFrame) -> pd.DataFrame:
    vr_code = str(load_config("territories.yml", root)["volta_redonda"]["ibge_code_7"])
    group_columns = ["age_group", "sex"]
    total = municipality.groupby(group_columns, as_index=False)["population"].sum()
    total["geography"] = "rj_total"
    vr = municipality.loc[municipality["municipality_code_ibge"] == vr_code]
    if vr.empty:
        raise ValueError("Volta Redonda is missing from age-sex population payload")
    vr = vr.groupby(group_columns, as_index=False)["population"].sum()
    vr["geography"] = "volta_redonda"
    rest = municipality.loc[municipality["municipality_code_ibge"] != vr_code]
    rest = rest.groupby(group_columns, as_index=False)["population"].sum()
    rest["geography"] = "rest_of_rj_excluding_vr"
    denominator = pd.concat([total, vr, rest], ignore_index=True)
    denominator.insert(0, "year", YEAR)
    denominator["unit"] = "pessoas"
    return denominator[
        ["year", "geography", "age_group", "sex", "population", "unit"]
    ].sort_values(["geography", "age_group", "sex"]).reset_index(drop=True)


def _write_report(
    root: Path,
    municipality: pd.DataFrame,
    denominator: pd.DataFrame,
    metadata: dict[str, object],
) -> Path:
    report = root / "reports" / "technical" / "denominadores_idade_sexo_2022.md"
    lines = [
        "# Denominadores por idade e sexo — Censo 2022",
        "",
        f"Execução: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "Os denominadores vêm da tabela 9514 da SIDRA, variável população "
        "residente, sexo masculino/feminino, forma de declaração da idade total. "
        "Os grupos foram agregados para coincidir com os grupos etários do SIM.",
        "",
        f"- Municípios RJ validados: **{municipality['municipality_code_ibge'].nunique()}**.",
        f"- Linhas municipais harmonizadas: **{len(municipality)}**.",
        f"- Linhas agregadas por território: **{len(denominator)}**.",
        f"- Arquivos brutos consultados: **{metadata['input_file_count']}**.",
        "",
        "## Denominadores agregados",
        "",
        "| território | idade | sexo | população |",
        "|---|---|---|---:|",
    ]
    lines.extend(
        f"| {row.geography} | {row.age_group} | {row.sex} | {row.population} |"
        for row in denominator.itertuples(index=False)
    )
    lines.extend(
        [
            "",
            "O total do RJ é a soma dos 92 municípios; o restante do RJ é a soma "
            "dos 91 municípios após retirar Volta Redonda pelo código IBGE 3306305.",
            "A população com idade ou sexo ignorados não é criada artificialmente; "
            "ela permanece fora dos denominadores específicos.",
        ]
    )
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def harmonize_age_sex_population(root: Path) -> tuple[Path, Path, Path]:
    raw_paths = sorted((root / "data" / "raw").glob(f"ibge_sidra_9514_age_sex_{YEAR}_rj_*.json"))
    if not raw_paths:
        raise FileNotFoundError("no SIDRA age-sex raw payloads found")
    frames = [_read_payload(path, root) for path in raw_paths]
    municipality = pd.concat(frames, ignore_index=True)
    duplicates = int(
        municipality.duplicated(["municipality_code_ibge", "age_group", "sex"]).sum()
    )
    expected_codes = set(_municipality_codes(root))
    observed_codes = set(municipality["municipality_code_ibge"].unique())
    if observed_codes != expected_codes:
        raise ValueError(
            f"age-sex payload municipality mismatch; missing={sorted(expected_codes - observed_codes)}, "
            f"unexpected={sorted(observed_codes - expected_codes)}"
        )
    expected_rows = len(expected_codes) * len(AGE_GROUPS) * len(SEX_CODES)
    if len(municipality) != expected_rows or duplicates:
        raise ValueError(
            f"expected {expected_rows} unique age-sex rows, got {len(municipality)} with {duplicates} duplicates"
        )
    denominator = _aggregate_denominators(root, municipality)
    processed = root / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    municipality_path = processed / "population_age_sex_2022.parquet"
    denominator_path = processed / "population_age_sex_denominators_2022.parquet"
    municipality.to_parquet(municipality_path, index=False)
    denominator.to_parquet(denominator_path, index=False)
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "validated_census_2022_age_sex_denominators",
        "year": YEAR,
        "municipality_count": int(municipality["municipality_code_ibge"].nunique()),
        "municipality_rows": int(len(municipality)),
        "denominator_rows": int(len(denominator)),
        "duplicate_rows": duplicates,
        "sidra_zero_marker_count": int(municipality["sidra_zero_marker_count"].sum()),
        "input_file_count": len(raw_paths),
        "input_files": [
            {"path": str(path.relative_to(root)), "sha256": sha256_file(path)}
            for path in raw_paths
        ],
        "municipality_output": {
            "path": str(municipality_path.relative_to(root)),
            "sha256": sha256_file(municipality_path),
        },
        "denominator_output": {
            "path": str(denominator_path.relative_to(root)),
            "sha256": sha256_file(denominator_path),
        },
        "rules": {
            "table": TABLE_ID,
            "variable": VARIABLE_ID,
            "sex_codes": SEX_CODES,
            "age_groups": AGE_GROUPS,
            "territory": "92 RJ municipalities; rest excludes IBGE 3306305",
        },
        "notes": [
            "This is a 2022 Census denominator and is not interpolated to other years.",
            "The age groups are harmonized to the SIM groups, not directly published as rates by the source.",
            "No unknown-age or unknown-sex denominator is invented.",
            "SIDRA '-' markers are treated as zero population cells and counted in the manifest.",
        ],
    }
    manifest_path = root / "reports" / "quality" / "population_age_sex_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = _write_report(root, municipality, denominator, metadata)
    return municipality_path, denominator_path, report_path
