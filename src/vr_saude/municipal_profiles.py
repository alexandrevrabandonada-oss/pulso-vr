from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import duckdb
from scipy.stats import chi2

from .config import load_config
from .mortality import period_status
from .outcomes import _matches_cid, _normalize_code
from .population_age_sex import AGE_GROUPS
from .provenance import sha256_file
from .rates import RATE_MULTIPLIER


YEAR = 2022
SEXES = ["masculino", "feminino"]
SMALL_CELL_THRESHOLD = 5
PROFILE_OUTCOME_SECTIONS = ("respiratory", "cardiovascular", "cardiorespiratory", "cancer")


def _definitions(root: Path) -> list[dict[str, object]]:
    config = load_config("outcomes.yml", root)
    definitions = [
        item
        for section in PROFILE_OUTCOME_SECTIONS
        for item in config.get(section, [])
        if "SIM" in item.get("source", []) and item.get("code_ranges") and item["id"] != "covid19"
    ]
    if len(definitions) != 30:
        raise ValueError(f"expected 30 public SIM profile outcomes, found {len(definitions)}")
    return definitions


def complementary_suppression(frame: pd.DataFrame) -> pd.DataFrame:
    """Protect a lone primary suppression within each public profile stratum."""

    result = frame.copy()
    result["suppression_status"] = "published"
    result.loc[result["count"] < SMALL_CELL_THRESHOLD, "suppression_status"] = "suppressed"
    keys = ["outcome_id", "age_group", "sex"]
    for _, indexes in result.groupby(keys, sort=False).groups.items():
        group = result.loc[indexes]
        suppressed = group["suppression_status"].eq("suppressed")
        if int(suppressed.sum()) != 1:
            continue
        candidates = group.loc[~suppressed & group["count"].ge(SMALL_CELL_THRESHOLD)]
        if candidates.empty:
            continue
        complementary_index = candidates.sort_values(
            ["count", "municipality_code_ibge"], kind="stable"
        ).index[0]
        result.loc[complementary_index, "suppression_status"] = "suppressed_complementary"
    return result


def apply_profile_applicability(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    not_applicable = (
        (result["outcome_id"].eq("cervix") & result["sex"].eq("masculino"))
        | (result["outcome_id"].eq("prostate") & result["sex"].eq("feminino"))
    )
    result.loc[not_applicable, "suppression_status"] = "not_applicable"
    return result


def _load_inputs(root: Path) -> tuple[pd.DataFrame, Path, Path]:
    sim_path = root / "data" / "interim" / f"sim_{YEAR}_harmonized.parquet"
    population_path = root / "data" / "processed" / "population_age_sex_2022.parquet"
    if not sim_path.exists() or not population_path.exists():
        raise FileNotFoundError("municipal SIM profiles require harmonized SIM 2022 and Censo 2022 age-sex denominators")
    population = pd.read_parquet(population_path)
    return population, sim_path, population_path


def _cause_map(sim_path: Path, definitions: list[dict[str, object]]) -> pd.DataFrame:
    raw = pd.read_parquet(sim_path, columns=["underlying_cause"])
    causes = pd.Series(_normalize_code(raw["underlying_cause"]).unique(), dtype="string")
    rows: list[pd.DataFrame] = []
    for definition in definitions:
        selected = causes.loc[_matches_cid(causes, list(definition["code_ranges"]))]
        rows.append(pd.DataFrame({"cause": selected, "outcome_id": str(definition["id"])}))
    return pd.concat(rows, ignore_index=True).drop_duplicates()


def _classified_counts(sim_path: Path, definitions: list[dict[str, object]]) -> pd.DataFrame:
    connection = duckdb.connect(database=":memory:")
    connection.execute("SET threads TO 4")
    connection.register("cause_map", _cause_map(sim_path, definitions))
    path = str(sim_path).replace("'", "''")
    query = f"""
        WITH normalized AS (
          SELECT source_row_number,
                 trim(CAST(municipality_code_datasus AS VARCHAR)) AS municipality_code_datasus,
                 upper(replace(trim(CAST(underlying_cause AS VARCHAR)), '.', '')) AS cause,
                 trim(CAST(sex_raw AS VARCHAR)) AS sex_code,
                 try_cast(age_raw AS INTEGER) AS age_value
          FROM read_parquet('{path}')
          WHERE coalesce(residence_code_valid, false)
            AND regexp_full_match(trim(CAST(municipality_code_datasus AS VARCHAR)), '33[0-9]{{4}}')
        ), dimensions AS (
          SELECT *,
            CASE sex_code WHEN '1' THEN 'masculino' WHEN '2' THEN 'feminino' ELSE 'ignorado' END AS sex,
            CASE
              WHEN age_value BETWEEN 0 AND 364 THEN '<1'
              WHEN age_value BETWEEN 365 AND 399 THEN '1-4'
              WHEN age_value BETWEEN 400 AND 404 THEN CASE WHEN age_value=400 THEN '<1' ELSE '1-4' END
              WHEN age_value BETWEEN 405 AND 414 THEN '5-14'
              WHEN age_value BETWEEN 415 AND 424 THEN '15-24'
              WHEN age_value BETWEEN 425 AND 444 THEN '25-44'
              WHEN age_value BETWEEN 445 AND 464 THEN '45-64'
              WHEN age_value BETWEEN 465 AND 474 THEN '65-74'
              WHEN age_value BETWEEN 475 AND 499 THEN '75+'
              ELSE 'ignorado' END AS age_group
          FROM normalized
        ), classified AS (
          SELECT d.source_row_number, d.municipality_code_datasus, d.age_group, d.sex, m.outcome_id
          FROM dimensions d
          JOIN cause_map m USING (cause)
        )
        SELECT municipality_code_datasus, outcome_id, age_group, sex, count(*)::BIGINT AS count
        FROM classified
        GROUP BY ALL
    """
    try:
        return connection.execute(query).fetchdf()
    finally:
        connection.close()


def _build_rates(root: Path) -> tuple[pd.DataFrame, dict[str, object], Path, Path]:
    population, sim_path, population_path = _load_inputs(root)
    definitions = _definitions(root)
    classified = _classified_counts(sim_path, definitions)
    valid_datasus_codes = set(population["municipality_code_ibge"].astype(str).str[:6].unique())
    invalid_territory = classified.loc[~classified["municipality_code_datasus"].isin(valid_datasus_codes)]
    excluded_invalid_territory = invalid_territory.groupby("outcome_id")["count"].sum().astype(int).to_dict()
    classified = classified.loc[classified["municipality_code_datasus"].isin(valid_datasus_codes)].copy()
    classified_totals = classified.groupby("outcome_id")["count"].sum().astype(int).to_dict()
    valid_dimensions = classified["age_group"].isin(AGE_GROUPS) & classified["sex"].isin(SEXES)
    ignored_by_outcome = classified.loc[~valid_dimensions].groupby("outcome_id")["count"].sum().astype(int).to_dict()
    ignored_by_outcome = {str(item["id"]): int(ignored_by_outcome.get(str(item["id"]), 0)) for item in definitions}
    counts = classified.loc[valid_dimensions].groupby(
        ["municipality_code_datasus", "outcome_id", "age_group", "sex"], as_index=False
    )["count"].sum()

    denominator = population.loc[
        population["age_group"].isin(AGE_GROUPS) & population["sex"].isin(SEXES),
        ["municipality_code_ibge", "municipality_name", "age_group", "sex", "population"],
    ].copy()
    denominator["municipality_code_ibge"] = denominator["municipality_code_ibge"].astype(str)
    denominator["municipality_code_datasus"] = denominator["municipality_code_ibge"].str[:6]
    if denominator["municipality_code_ibge"].nunique() != 92 or len(denominator) != 92 * 8 * 2:
        raise ValueError("municipal age-sex denominator must contain 92 municipalities, 8 age groups and 2 sexes")
    outcomes = pd.DataFrame({"outcome_id": [str(item["id"]) for item in definitions]})
    rates = denominator.merge(outcomes, how="cross").merge(
        counts,
        on=["municipality_code_datasus", "outcome_id", "age_group", "sex"],
        how="left",
        validate="one_to_one",
    )
    rates["count"] = rates["count"].fillna(0).astype(int)
    count_values = rates["count"].to_numpy()
    lower_counts = 0.5 * chi2.ppf(0.025, 2 * count_values)
    lower_counts[count_values == 0] = 0.0
    upper_counts = 0.5 * chi2.ppf(0.975, 2 * (count_values + 1))
    rates["rate_per_100k"] = rates["count"] / rates["population"] * RATE_MULTIPLIER
    rates["rate_ci_lower_per_100k"] = lower_counts / rates["population"].to_numpy() * RATE_MULTIPLIER
    rates["rate_ci_upper_per_100k"] = upper_counts / rates["population"].to_numpy() * RATE_MULTIPLIER
    rates["year"] = YEAR
    status_by_outcome = {
        outcome: period_status(root, YEAR, outcome) for outcome in rates["outcome_id"].unique()
    }
    rates["period_status"] = rates["outcome_id"].map(status_by_outcome)
    rates = apply_profile_applicability(complementary_suppression(rates))

    reconciled = rates.groupby("outcome_id")["count"].sum().to_dict()
    expected = {key: value - ignored_by_outcome[key] for key, value in classified_totals.items()}
    mismatches = {key: {"expected": expected[key], "observed": int(reconciled.get(key, 0))} for key in expected if int(reconciled.get(key, 0)) != expected[key]}
    if mismatches:
        raise ValueError(f"municipal profile reconciliation failed: {mismatches}")
    quality = {
        "classified_deaths": classified_totals,
        "excluded_unknown_age_or_sex": ignored_by_outcome,
        "excluded_invalid_or_historical_municipality_code": {
            key: int(value) for key, value in excluded_invalid_territory.items()
        },
        "reconciled_publishable_dimension_deaths": {key: int(value) for key, value in reconciled.items()},
        "reconciliation_mismatches": mismatches,
    }
    rates = rates.sort_values(["outcome_id", "municipality_code_ibge", "age_group", "sex"]).reset_index(drop=True)
    return rates, quality, sim_path, population_path


def build_municipal_age_sex_profiles(root: Path) -> tuple[Path, Path, Path]:
    rates, quality, sim_path, population_path = _build_rates(root)
    output = root / "data" / "processed" / "sim_municipal_age_sex_rates_2022.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    rates.to_parquet(output, index=False)
    status_counts = rates["suppression_status"].value_counts().to_dict()
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "validated_sim_2022_municipal_age_sex_specific_rates",
        "year": YEAR,
        "municipality_count": int(rates["municipality_code_ibge"].nunique()),
        "outcome_count": int(rates["outcome_id"].nunique()),
        "rows": int(len(rates)),
        "age_groups": AGE_GROUPS,
        "sexes": SEXES,
        "suppression": {key: int(value) for key, value in status_counts.items()},
        "quality": quality,
        "output_path": str(output.relative_to(root)),
        "output_sha256": sha256_file(output),
        "input_files": [
            {"path": str(sim_path.relative_to(root)), "sha256": sha256_file(sim_path)},
            {"path": str(population_path.relative_to(root)), "sha256": sha256_file(population_path)},
        ],
        "rules": {
            "residence": "CODMUNRES validado para os 92 municípios do RJ",
            "rate": "óbitos pela causa básica / população residente do mesmo município, idade e sexo × 100.000",
            "interval": "IC 95% exato de Poisson",
            "suppression": "contagem <5 e supressão complementar quando houver uma única célula primária no estrato",
            "standardization": "taxa específica bruta; não padronizada",
        },
    }
    manifest_path = root / "reports" / "quality" / "sim_municipal_age_sex_profiles_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = root / "reports" / "technical" / "perfis_municipais_sim_2022.md"
    report_path.write_text(
        "\n".join([
            "# Perfis municipais por idade e sexo — SIM 2022", "",
            "Taxas específicas brutas de mortalidade de residentes, calculadas para 92 municípios e 30 indicadores SIM.", "",
            f"- Linhas analíticas: **{len(rates)}**.",
            f"- Células primárias protegidas: **{status_counts.get('suppressed', 0)}**.",
            f"- Supressões complementares: **{status_counts.get('suppressed_complementary', 0)}**.",
            "- Idade ou sexo ignorado é auditado, mas não recebe denominador inventado.",
            "- Mortalidade por câncer não representa incidência e estes dados não autorizam inferência causal.",
        ]) + "\n",
        encoding="utf-8",
    )
    return output, manifest_path, report_path
