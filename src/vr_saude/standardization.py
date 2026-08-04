from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from scipy.stats import norm

from .provenance import sha256_file

RATE_MULTIPLIER = 100_000
AGE_GROUPS = ["<1", "1-4", "5-14", "15-24", "25-44", "45-64", "65-74", "75+"]
SEXES = ["masculino", "feminino"]


def direct_standardized_rate(
    rates: pd.DataFrame,
    standard: pd.DataFrame,
    *,
    geography_column: str = "geography",
) -> pd.DataFrame:
    """Calculate direct standardized rates using one common population standard.

    ``rates`` must contain one row per geography/age/sex with ``count`` and
    ``population``. The function intentionally fails on missing cells rather
    than silently filling an age denominator.
    """
    required = {geography_column, "age_group", "sex", "count", "population"}
    missing = sorted(required - set(rates.columns))
    if missing:
        raise ValueError(f"age-specific numerator is missing columns: {missing}")
    standard_required = {"age_group", "sex", "population"}
    missing = sorted(standard_required - set(standard.columns))
    if missing:
        raise ValueError(f"standard population is missing columns: {missing}")

    standard = standard.loc[standard["age_group"].isin(AGE_GROUPS) & standard["sex"].isin(SEXES)].copy()
    standard = standard.groupby(["age_group", "sex"], as_index=False)["population"].sum()
    if standard.empty or (standard["population"] <= 0).any():
        raise ValueError("standard population must contain positive age-sex cells")
    standard_total = int(standard["population"].sum())
    standard["weight"] = standard["population"] / standard_total

    frame = rates.loc[rates["age_group"].isin(AGE_GROUPS) & rates["sex"].isin(SEXES)].copy()
    frame["count"] = pd.to_numeric(frame["count"], errors="raise")
    frame["population"] = pd.to_numeric(frame["population"], errors="raise")
    if (frame["count"] < 0).any() or (frame["population"] <= 0).any():
        raise ValueError("age-specific counts/populations must be non-negative/positive")
    keys = [geography_column, "age_group", "sex"]
    if frame.duplicated(keys).any():
        raise ValueError("age-specific numerator contains duplicate geography/age/sex cells")
    expected = set(standard[["age_group", "sex"]].itertuples(index=False, name=None))
    observed = set(frame[["age_group", "sex"]].itertuples(index=False, name=None))
    if expected != observed:
        raise ValueError("age-specific numerator does not cover exactly the standard age-sex cells")

    frame = frame.merge(
        standard.rename(columns={"population": "standard_population_cell"}),
        on=["age_group", "sex"],
        how="left",
        validate="many_to_one",
    )
    frame["specific_rate"] = frame["count"] / frame["population"] * RATE_MULTIPLIER
    frame["variance"] = (frame["weight"] ** 2) * frame["count"] / (frame["population"] ** 2) * RATE_MULTIPLIER**2
    result = frame.groupby(geography_column, as_index=False).agg(
        standardized_rate_per_100k=("specific_rate", lambda values: float((values * frame.loc[values.index, "weight"]).sum())),
        standardized_variance=("variance", "sum"),
        count=("count", "sum"),
        denominator=("population", "sum"),
    )
    z = float(norm.ppf(0.975))
    result["standardized_ci_low_per_100k"] = (result["standardized_rate_per_100k"] - z * result["standardized_variance"].pow(0.5)).clip(lower=0)
    result["standardized_ci_high_per_100k"] = result["standardized_rate_per_100k"] + z * result["standardized_variance"].pow(0.5)
    result["standard_population"] = "Brazil Censo 2022"
    result["standard_population_total"] = standard_total
    return result.drop(columns=["standardized_variance"])


def build_sim_neurological_standardized_rates(root: Path, year: int = 2022) -> tuple[Path, Path, Path]:
    """Build 2022 SIM municipal standardized rates when Brazil standard exists."""
    if year != 2022:
        raise ValueError("the configured municipal age-sex standard is available only for 2022")
    rates_path = root / "data" / "processed" / "sim_municipal_age_sex_rates_2022.parquet"
    standard_path = root / "data" / "processed" / "population_age_sex_brazil_2022.parquet"
    if not rates_path.exists():
        raise FileNotFoundError(f"municipal age-sex rates are missing: {rates_path}")
    if not standard_path.exists():
        raise FileNotFoundError(f"Brazil 2022 standard population is missing: {standard_path}")
    rates = pd.read_parquet(rates_path)
    rates = rates.loc[rates["outcome_id"].isin(["alzheimer", "dementias_all"])].copy()
    standard = pd.read_parquet(standard_path)
    rows: list[pd.DataFrame] = []
    for outcome_id, outcome_frame in rates.groupby("outcome_id", sort=True):
        result = direct_standardized_rate(
            outcome_frame.rename(columns={"municipality_code_ibge": "geography"}),
            standard,
        )
        result.insert(0, "year", year)
        result.insert(1, "outcome_id", outcome_id)
        rows.append(result)
    if not rows:
        raise ValueError("no Alzheimer/dementia municipal age-sex rows available")
    output = root / "data" / "processed" / "sim_neurological_standardized_rates_2022.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    result = pd.concat(rows, ignore_index=True).sort_values(["outcome_id", "geography"])
    result.to_parquet(output, index=False)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "validated_sim_2022_direct_standardized_rates",
        "year": year,
        "standard_population": "Brazil Censo 2022",
        "outcome_ids": sorted(result["outcome_id"].unique().tolist()),
        "municipalities": int(result["geography"].nunique()),
        "output_path": str(output.relative_to(root)),
        "output_sha256": sha256_file(output),
        "input_files": [
            {"path": str(rates_path.relative_to(root)), "sha256": sha256_file(rates_path)},
            {"path": str(standard_path.relative_to(root)), "sha256": sha256_file(standard_path)},
        ],
        "notes": [
            "Direct standardization is published only for 2022 because municipal age-sex denominators are not available as an annual series.",
            "The rate is not calculated for SIA establishment production.",
            "Cells below five remain protected at public publication time.",
        ],
    }
    manifest_path = root / "reports" / "quality" / "sim_neurological_standardized_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = root / "reports" / "technical" / "taxas_padronizadas_alzheimer_2022.md"
    report_path.write_text(
        "# Taxas padronizadas de Alzheimer e demências — SIM 2022\n\n"
        "Taxas diretamente padronizadas por idade e sexo usando a população do Brasil no Censo 2022. "
        "A série anual permanece bruta; não há interpolação de denominadores etários.\n",
        encoding="utf-8",
    )
    return output, manifest_path, report_path
