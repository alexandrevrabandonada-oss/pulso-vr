from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

from .config import load_config
from .provenance import sha256_file


SIVEP_CLASSIFICATION_CODES = {
    "influenza": "1",
    "covid19": "5",
}
SIVEP_OUTCOME_CODES = {
    "1": "recuperado",
    "2": "óbito por SRAG",
    "3": "óbito por outra causa",
    "9": "ignorado",
    "": "sem informação",
}
AGE_GROUPS = ["<1", "1-4", "5-14", "15-24", "25-44", "45-64", "65-74", "75+", "ignorado"]
OUTCOME_SECTIONS = ("respiratory", "cardiovascular", "cardiorespiratory", "cancer", "neurological")


def _normalize_code(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .fillna("")
        .str.upper()
        .str.replace(".", "", regex=False)
        .str.strip()
    )


def _matches_cid(codes: pd.Series, ranges: list[str]) -> pd.Series:
    result = pd.Series(False, index=codes.index)
    for expression in ranges:
        expression = expression.upper().replace(".", "").replace(" ", "")
        if "-" not in expression:
            # A three-character CID-10 category (e.g. C50) includes its
            # four-character subcategories (e.g. C509). Longer expressions
            # remain exact to preserve codes such as U071.
            if len(expression) == 3:
                result |= codes.str.startswith(expression)
            else:
                result |= codes.eq(expression)
            continue
        start, end = expression.split("-", 1)
        if len(start) < 3 or len(end) < 3 or start[0] != end[0]:
            raise ValueError(f"unsupported CID range: {expression}")
        letters = codes.str[0].eq(start[0])
        values = pd.to_numeric(codes.str[1:3], errors="coerce")
        result |= letters & values.between(int(start[1:3]), int(end[1:3]), inclusive="both")
    return result


def _definitions(root: Path, source: str) -> list[dict[str, Any]]:
    config = load_config("outcomes.yml", root)
    definitions: list[dict[str, Any]] = []
    for section in OUTCOME_SECTIONS:
        for item in config.get(section, []):
            if source in item.get("source", []) and item.get("code_ranges"):
                definitions.append(item)
    return definitions


def _age_groups_from_years(years: pd.Series) -> pd.Series:
    values = pd.Series("ignorado", index=years.index, dtype="string")
    values.loc[years.notna() & years.lt(1)] = "<1"
    values.loc[years.ge(1) & years.lt(5)] = "1-4"
    values.loc[years.ge(5) & years.lt(15)] = "5-14"
    values.loc[years.ge(15) & years.lt(25)] = "15-24"
    values.loc[years.ge(25) & years.lt(45)] = "25-44"
    values.loc[years.ge(45) & years.lt(65)] = "45-64"
    values.loc[years.ge(65) & years.lt(75)] = "65-74"
    values.loc[years.ge(75)] = "75+"
    return values


def _sim_age_groups(raw: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(raw, errors="coerce")
    years = pd.Series(float("nan"), index=raw.index)
    years.loc[numeric.between(0, 399, inclusive="both")] = numeric.loc[
        numeric.between(0, 399, inclusive="both")
    ] / 365
    years.loc[numeric.between(400, 499, inclusive="both")] = numeric.loc[
        numeric.between(400, 499, inclusive="both")
    ] - 400
    return _age_groups_from_years(years)


def _sivep_age_groups(raw: pd.Series, unit_raw: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(raw, errors="coerce")
    units = _normalize_code(unit_raw)
    years = pd.Series(float("nan"), index=raw.index)
    years.loc[units.eq("3")] = numeric.loc[units.eq("3")]
    years.loc[units.eq("2")] = numeric.loc[units.eq("2")] / 12
    years.loc[units.eq("1")] = numeric.loc[units.eq("1")] / 365
    return _age_groups_from_years(years)


def _sex_labels(raw: pd.Series, source: str) -> pd.Series:
    values = _normalize_code(raw)
    if source == "SIM":
        return values.map({"1": "masculino", "2": "feminino"}).fillna("ignorado")
    return values.map({"M": "masculino", "F": "feminino"}).fillna("ignorado")


def _geography(code: pd.Series, vr_code: str) -> pd.Series:
    code = _normalize_code(code)
    in_rj = code.str.fullmatch(r"33\d{4}").fillna(False)
    in_brazil = code.str.fullmatch(r"\d{6}").fillna(False)
    geography = pd.Series("outside_brazil", index=code.index, dtype="string")
    geography.loc[in_brazil & ~in_rj] = "rest_of_brazil_excluding_rj"
    geography.loc[in_rj & code.eq(vr_code)] = "volta_redonda"
    geography.loc[in_rj & code.ne(vr_code)] = "rest_of_rj_excluding_vr"
    return geography


def _classification_rows(
    chunk: pd.DataFrame,
    source: str,
    root: Path,
    vr_code: str,
    source_path: str,
    source_sha256: str,
) -> pd.DataFrame:
    geography = _geography(chunk["municipality_code_datasus"], vr_code)
    in_rj = geography.isin(["volta_redonda", "rest_of_rj_excluding_vr"])
    eligible = geography.ne("outside_brazil") if source == "SIM" else in_rj
    if not eligible.any():
        return pd.DataFrame()
    if source == "SIM":
        codes = _normalize_code(chunk["underlying_cause"])
        sex = _sex_labels(chunk["sex_raw"], source)
        age_group = _sim_age_groups(chunk["age_raw"])
        status = pd.Series("óbito", index=chunk.index, dtype="string")
        definitions = _definitions(root, source)
        outcome_masks = {
            item["id"]: _matches_cid(codes, item["code_ranges"])
            for item in definitions
        }
        labels = {item["id"]: item["label"] for item in definitions}
        unit = "óbito de residente no SIM; causa básica"
    else:
        classification = _normalize_code(chunk["final_classification_raw"])
        sex = _sex_labels(chunk["sex_raw"], source)
        age_group = _sivep_age_groups(chunk["age_raw"], chunk["age_unit_raw"])
        status = _normalize_code(chunk["outcome_raw"]).map(SIVEP_OUTCOME_CODES).fillna("sem informação")
        outcome_masks = {
            "srag": pd.Series(True, index=chunk.index),
            "influenza": classification.eq(SIVEP_CLASSIFICATION_CODES["influenza"]),
            "covid19": classification.eq(SIVEP_CLASSIFICATION_CODES["covid19"]),
        }
        labels = {
            "srag": "Síndrome Respiratória Aguda Grave",
            "influenza": "SRAG por influenza",
            "covid19": "SRAG por Covid-19",
        }
        unit = "notificação de SRAG de residente; vigilância, não incidência"
    rows: list[pd.DataFrame] = []
    for outcome_id, mask in outcome_masks.items():
        selected = eligible & mask
        if not selected.any():
            continue
        frame = pd.DataFrame(
            {
                "source": source,
                "source_year": chunk["source_year"].astype(int),
                "geography": geography,
                "outcome_id": outcome_id,
                "outcome_label": labels[outcome_id],
                "sex": sex,
                "age_group": age_group,
                "outcome_status": status,
                "unit": unit,
                "source_path": source_path,
                "source_sha256": source_sha256,
            },
            index=chunk.index,
        ).loc[selected]
        group_columns = [
            "source",
            "source_year",
            "geography",
            "outcome_id",
            "outcome_label",
            "sex",
            "age_group",
            "outcome_status",
            "unit",
            "source_path",
            "source_sha256",
        ]
        rows.append(frame.groupby(group_columns, dropna=False).size().reset_index(name="count"))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _manifest_input_info(root: Path) -> dict[str, dict[str, Any]]:
    manifest_path = root / "reports" / "quality" / "harmonization_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"harmonization manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {item["output_path"]: item for item in manifest["results"]}


def _source_files(root: Path) -> list[Path]:
    return sorted(
        [*((root / "data" / "interim").glob("sim_*_harmonized.parquet")),
         *((root / "data" / "interim").glob("sivep_*_harmonized.parquet"))]
    )


def _rj_totals(data: pd.DataFrame) -> pd.DataFrame:
    data = data.loc[data["geography"].isin(["volta_redonda", "rest_of_rj_excluding_vr"])]
    keys = [column for column in data.columns if column not in {"geography", "count"}]
    total = data.groupby(keys, dropna=False, as_index=False)["count"].sum()
    total["geography"] = "rj_total"
    return total[data.columns]


def _brazil_totals(data: pd.DataFrame) -> pd.DataFrame:
    data = data.loc[
        data["geography"].isin(
            ["volta_redonda", "rest_of_rj_excluding_vr", "rest_of_brazil_excluding_rj"]
        )
    ]
    keys = [column for column in data.columns if column not in {"geography", "count"}]
    total = data.groupby(keys, dropna=False, as_index=False)["count"].sum()
    total["geography"] = "brazil_total"
    return total[data.columns]


def _write_outcome_report(root: Path, data: pd.DataFrame, metadata: dict[str, Any]) -> Path:
    report = root / "reports" / "technical" / "desfechos_sim_sivep.md"
    totals = (
        data.groupby(["source", "source_year", "geography", "outcome_id", "outcome_label"], as_index=False)["count"]
        .sum()
        .sort_values(["source", "source_year", "outcome_id", "geography"])
    )
    table_rows = []
    for row in totals.itertuples(index=False):
        display_count = "<5" if row.count < 5 else str(int(row.count))
        table_rows.append(f"| {row.source} | {row.source_year} | {row.geography} | {row.outcome_id} | {display_count} |")
    lines = [
        "# Desfechos classificados no SIM e SIVEP",
        "",
        f"Execução: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "O SIM é contado como óbito de residente pela causa básica. O SIVEP é contado como "
        "notificação de SRAG de residente; não é incidência populacional. Volta Redonda e o "
        "restante do RJ são definidos pelo código DATASUS de residência, e o total do RJ é "
        "a soma dos dois grupos.",
        "",
        f"- Linhas analíticas agregadas: **{len(data)}**.",
        f"- Arquivos de entrada: **{metadata['input_file_count']}**.",
        f"- Residências RJ classificadas: **{metadata['residence_rj_rows']}**.",
        f"- Residências VR classificadas: **{metadata['residence_vr_rows']}**.",
        "- Células menores que cinco são exibidas como `<5` neste relatório.",
        "",
        "## Totais por fonte e desfecho",
        "",
        "| fonte | ano | território | desfecho | contagem |",
        "|---|---:|---|---|---:|",
        *table_rows,
        "",
        "## Regras SIVEP",
        "",
        "- `srag`: todas as notificações elegíveis do banco SIVEP.",
        "- `influenza`: `CLASSI_FIN=1`.",
        "- `covid19`: `CLASSI_FIN=5`.",
        "- `TP_IDADE=1/2/3` é tratado como dia/mês/ano para formar grupos etários amplos.",
        "",
        "SIM 2010–2024 foi harmonizado como série anual adquirida; SIVEP 2019–2026 foi "
        "adquirido em versões datadas, com 2026 parcial e provisório. Causas múltiplas não são usadas "
        "para classificar estes resultados. "
        "Não há ajuste, padronização etária, incidência ou atribuição causal.",
    ]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_outcome_counts(root: Path) -> tuple[Path, Path, Path]:
    vr_code = str(load_config("territories.yml", root)["volta_redonda"]["datasus_code_6_expected"])
    input_info = _manifest_input_info(root)
    all_rows: list[pd.DataFrame] = []
    input_stats: list[dict[str, Any]] = []
    residence_rj_rows = 0
    residence_vr_rows = 0
    for path in _source_files(root):
        info = input_info.get(str(path.relative_to(root)))
        if not info:
            raise ValueError(f"input not present in harmonization manifest: {path}")
        source = info["source"]
        source_path = info["input_path"]
        source_sha256 = info["input_sha256"]
        source_rows = 0
        source_rj = 0
        source_vr = 0
        parquet = pq.ParquetFile(path)
        columns = [
            "source_year",
            "municipality_code_datasus",
            "sex_raw",
            "age_raw",
            "underlying_cause" if source == "SIM" else "final_classification_raw",
            "outcome_raw" if source != "SIM" else "death_type_raw",
        ]
        if source != "SIM":
            columns.append("age_unit_raw")
        for batch in parquet.iter_batches(columns=columns, batch_size=200_000):
            chunk = batch.to_pandas()
            source_rows += len(chunk)
            geography = _geography(chunk["municipality_code_datasus"], vr_code)
            source_rj += int(geography.isin(["volta_redonda", "rest_of_rj_excluding_vr"]).sum())
            source_vr += int(geography.eq("volta_redonda").sum())
            rows = _classification_rows(chunk, source, root, vr_code, source_path, source_sha256)
            if not rows.empty:
                all_rows.append(rows)
        input_stats.append(
            {
                "source": source,
                "source_year": info["source_year"],
                "input_path": source_path,
                "input_sha256": source_sha256,
                "harmonized_path": str(path.relative_to(root)),
                "harmonized_sha256": sha256_file(path),
                "rows": source_rows,
                "residence_rj_rows": source_rj,
                "residence_vr_rows": source_vr,
            }
        )
        residence_rj_rows += source_rj
        residence_vr_rows += source_vr
    if not all_rows:
        raise ValueError("no classified RJ outcome rows were produced")
    data = pd.concat(all_rows, ignore_index=True)
    group_columns = [column for column in data.columns if column != "count"]
    data = data.groupby(group_columns, dropna=False, as_index=False)["count"].sum()
    data = pd.concat([data, _rj_totals(data), _brazil_totals(data)], ignore_index=True)
    data = data.sort_values(["source", "source_year", "outcome_id", "geography", "sex", "age_group"]).reset_index(drop=True)
    output = root / "data" / "processed" / "outcome_counts_sim_sivep.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_parquet(output, index=False)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "interim_outcome_counts_no_incidence_estimate",
        "rows": int(len(data)),
        "outcome_ids": sorted(data["outcome_id"].unique().tolist()),
        "input_file_count": len(input_stats),
        "residence_rj_rows": residence_rj_rows,
        "residence_vr_rows": residence_vr_rows,
        "input_files": input_stats,
        "output_path": str(output.relative_to(root)),
        "output_sha256": sha256_file(output),
        "rules": {
            "sim": "underlying_cause classified by CID-10 ranges from config/outcomes.yml",
            "sivep_srag": "all eligible SIVEP records",
            "sivep_influenza": "CLASSI_FIN=1",
            "sivep_covid19": "CLASSI_FIN=5",
            "territory": "residence code; VR=330630; rest RJ excludes VR; Brazil total aggregates all valid Brazilian municipality codes",
        },
        "notes": [
            "SIM records are deaths, not incident cancer or respiratory cases.",
            "SIVEP records are surveillance notifications, not population incidence.",
            "Age groups are broad and use TP_IDADE for SIVEP; no age-specific rates are calculated here.",
            "Counts below five are suppressed in the technical presentation, not in the internal Parquet.",
            "No causal interpretation is authorized.",
        ],
    }
    manifest_path = root / "reports" / "quality" / "outcome_counts_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = _write_outcome_report(
        root,
        data,
        {"input_file_count": len(input_stats), "residence_rj_rows": residence_rj_rows, "residence_vr_rows": residence_vr_rows},
    )
    return output, manifest_path, report_path
