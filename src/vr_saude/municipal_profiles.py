from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from scipy.stats import chi2

from .config import load_config
from .mortality import period_status
from .outcomes import _matches_cid, _normalize_code, _sex_labels, _sim_age_groups
from .population_age_sex import AGE_GROUPS
from .provenance import sha256_file
from .rates import RATE_MULTIPLIER


YEAR = 2022
SEXES = ["masculino", "feminino"]
SMALL_CELL_THRESHOLD = 5


def _definitions(root: Path) -> list[dict[str, object]]:
    config = load_config("outcomes.yml", root)
    definitions = [
        item
        for section in ("respiratory", "cardiovascular", "cardiorespiratory", "cancer")
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


def _load_inputs(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, Path, Path]:
    sim_path = root / "data" / "interim" / f"sim_{YEAR}_harmonized.parquet"
    population_path = root / "data" / "processed" / "population_age_sex_2022.parquet"
    if not sim_path.exists() or not population_path.exists():
        raise FileNotFoundError("municipal SIM profiles require harmonized SIM 2022 and Censo 2022 age-sex denominators")
    sim = pd.read_parquet(
        sim_path,
        columns=["municipality_code_datasus", "residence_code_valid", "sex_raw", "age_raw", "underlying_cause"],
    )
    population = pd.read_parquet(population_path)
    return sim, population, sim_path, population_path


def _build_rates(root: Path) -> tuple[pd.DataFrame, dict[str, object], Path, Path]:
    sim, population, sim_path, population_path = _load_inputs(root)
    definitions = _definitions(root)
    residence = _normalize_code(sim["municipality_code_datasus"])
    eligible_residence = sim["residence_code_valid"].fillna(False) & residence.str.fullmatch(r"33\d{4}")
    sex = _sex_labels(sim["sex_raw"], "SIM")
    age_group = _sim_age_groups(sim["age_raw"])
    codes = _normalize_code(sim["underlying_cause"])
    distinct_codes = pd.Series(codes.unique(), dtype="string")
    valid_dimensions = eligible_residence & sex.isin(SEXES) & age_group.isin(AGE_GROUPS)

    lookup_rows: list[pd.DataFrame] = []
    for definition in definitions:
        outcome_id = str(definition["id"])
        matching = distinct_codes.loc[_matches_cid(distinct_codes, list(definition["code_ranges"]))]
        lookup_rows.append(pd.DataFrame({"underlying_cause": matching, "outcome_id": outcome_id}))
    lookup = pd.concat(lookup_rows, ignore_index=True)
    base = pd.DataFrame({
        "municipality_code_datasus": residence.loc[eligible_residence],
        "underlying_cause": codes.loc[eligible_residence],
        "age_group": age_group.loc[eligible_residence],
        "sex": sex.loc[eligible_residence],
        "dimensions_valid": valid_dimensions.loc[eligible_residence],
        "count": 1,
    }).groupby(
        ["municipality_code_datasus", "underlying_cause", "age_group", "sex", "dimensions_valid"],
        as_index=False,
        dropna=False,
    )["count"].sum()
    classified = base.merge(lookup, on="underlying_cause", how="inner", validate="many_to_many")
    classified_totals = classified.groupby("outcome_id")["count"].sum().astype(int).to_dict()
    ignored_by_outcome = (
        classified.loc[~classified["dimensions_valid"]].groupby("outcome_id")["count"].sum().astype(int).to_dict()
    )
    ignored_by_outcome = {str(item["id"]): int(ignored_by_outcome.get(str(item["id"]), 0)) for item in definitions}
    counts = classified.loc[classified["dimensions_valid"]].groupby(
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
    rates["period_status"] = [period_status(root, YEAR, outcome) for outcome in rates["outcome_id"]]
    rates = complementary_suppression(rates)

    reconciled = rates.groupby("outcome_id")["count"].sum().to_dict()
    expected = {key: value - ignored_by_outcome[key] for key, value in classified_totals.items()}
    mismatches = {key: {"expected": expected[key], "observed": int(reconciled.get(key, 0))} for key in expected if int(reconciled.get(key, 0)) != expected[key]}
    if mismatches:
        raise ValueError(f"municipal profile reconciliation failed: {mismatches}")
    quality = {
        "classified_deaths": classified_totals,
        "excluded_unknown_age_or_sex": ignored_by_outcome,
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
