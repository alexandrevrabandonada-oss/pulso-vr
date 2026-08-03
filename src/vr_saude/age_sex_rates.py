from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .mortality import RATE_MULTIPLIER, _rate_ratio_interval, period_status
from .population_age_sex import AGE_GROUPS
from .provenance import sha256_file
from .rates import poisson_count_interval


YEAR = 2022
GEOGRAPHIES = ["rj_total", "volta_redonda", "rest_of_rj_excluding_vr"]
REPORT_OUTCOMES = [
    "all_malignant_neoplasms",
    "resp_all",
    "lung",
    "bladder",
    "non_hodgkin_lymphoma",
    "leukemia",
    "colorectal",
]
SEXES = ["masculino", "feminino"]


def _load_inputs(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, Path, Path]:
    counts_path = root / "data" / "processed" / "outcome_counts_sim_sivep.parquet"
    denominator_path = root / "data" / "processed" / "population_age_sex_denominators_2022.parquet"
    if not counts_path.exists():
        raise FileNotFoundError(f"outcome counts Parquet is missing: {counts_path}")
    if not denominator_path.exists():
        raise FileNotFoundError(f"age-sex denominator Parquet is missing: {denominator_path}")
    counts = pd.read_parquet(counts_path)
    counts = counts.loc[
        (counts["source"] == "SIM")
        & (counts["source_year"] == YEAR)
        & counts["geography"].isin(GEOGRAPHIES)
        & counts["age_group"].isin(AGE_GROUPS)
        & counts["sex"].isin(SEXES)
    ].copy()
    denominator = pd.read_parquet(denominator_path)
    denominator = denominator.loc[
        denominator["year"].eq(YEAR)
        & denominator["geography"].isin(GEOGRAPHIES)
        & denominator["age_group"].isin(AGE_GROUPS)
        & denominator["sex"].isin(SEXES)
    ].copy()
    if counts.empty or denominator.empty:
        raise ValueError("age-sex rate inputs are empty")
    counts["count"] = pd.to_numeric(counts["count"], errors="raise").astype(int)
    denominator["population"] = pd.to_numeric(denominator["population"], errors="raise").astype(int)
    return counts, denominator, counts_path, denominator_path


def _build_rates(root: Path) -> tuple[pd.DataFrame, Path, Path]:
    counts, denominator, counts_path, denominator_path = _load_inputs(root)
    count_totals = (
        counts.groupby(
            ["outcome_id", "outcome_label", "geography", "age_group", "sex"],
            as_index=False,
        )["count"]
        .sum()
    )
    outcomes = counts[["outcome_id", "outcome_label"]].drop_duplicates()
    grid = denominator[["geography", "age_group", "sex", "population"]].merge(
        outcomes,
        how="cross",
    )
    rates = grid.merge(
        count_totals,
        on=["outcome_id", "outcome_label", "geography", "age_group", "sex"],
        how="left",
        validate="many_to_one",
    )
    rates["count"] = rates["count"].fillna(0).astype(int)
    lower_counts: list[float] = []
    upper_counts: list[float] = []
    for count in rates["count"]:
        lower, upper = poisson_count_interval(int(count))
        lower_counts.append(lower)
        upper_counts.append(upper)
    rates["rate_per_100k"] = rates["count"] / rates["population"] * RATE_MULTIPLIER
    rates["rate_ci_lower_per_100k"] = [
        value / population * RATE_MULTIPLIER
        for value, population in zip(lower_counts, rates["population"])
    ]
    rates["rate_ci_upper_per_100k"] = [
        value / population * RATE_MULTIPLIER
        for value, population in zip(upper_counts, rates["population"])
    ]
    rates["year"] = YEAR
    rates["period_status"] = [
        period_status(root, YEAR, outcome_id) for outcome_id in rates["outcome_id"]
    ]
    comparison = rates.pivot_table(
        index=["year", "outcome_id", "age_group", "sex"],
        columns="geography",
        values=["count", "rate_per_100k", "population"],
        aggfunc="first",
    )
    comparison.columns = ["_".join(column).strip() for column in comparison.columns.to_flat_index()]
    comparison = comparison.reset_index()
    rates = rates.merge(
        comparison,
        on=["year", "outcome_id", "age_group", "sex"],
        how="left",
        validate="many_to_one",
    )
    rates["rate_ratio_vr_vs_rest"] = (
        rates["rate_per_100k_volta_redonda"]
        / rates["rate_per_100k_rest_of_rj_excluding_vr"]
    ).replace([float("inf"), -float("inf")], float("nan"))
    rates["rate_difference_vr_minus_rest_per_100k"] = (
        rates["rate_per_100k_volta_redonda"]
        - rates["rate_per_100k_rest_of_rj_excluding_vr"]
    )
    intervals = [
        _rate_ratio_interval(int(vr), int(rest), pop_vr, pop_rest)
        for vr, rest, pop_vr, pop_rest in zip(
            rates["count_volta_redonda"],
            rates["count_rest_of_rj_excluding_vr"],
            rates["population_volta_redonda"],
            rates["population_rest_of_rj_excluding_vr"],
        )
    ]
    rates["rate_ratio_ci_lower"] = [interval[0] for interval in intervals]
    rates["rate_ratio_ci_upper"] = [interval[1] for interval in intervals]
    rates = rates.sort_values(["outcome_id", "age_group", "sex", "geography"]).reset_index(drop=True)
    return rates, counts_path, denominator_path


def _write_report(root: Path, rates: pd.DataFrame) -> Path:
    report = root / "reports" / "technical" / "taxas_sim_idade_sexo_2022.md"
    selected = rates.loc[
        rates["outcome_id"].isin(REPORT_OUTCOMES)
        & rates["geography"].isin(["volta_redonda", "rest_of_rj_excluding_vr"])
    ].copy()
    age_order = {value: index for index, value in enumerate(AGE_GROUPS)}
    sex_order = {"masculino": 0, "feminino": 1}
    selected["age_order"] = selected["age_group"].map(age_order)
    selected["sex_order"] = selected["sex"].map(sex_order)
    rows = []
    for row in selected.sort_values(
        ["outcome_id", "geography", "age_order", "sex_order"]
    ).itertuples(index=False):
        if row.count < 5:
            count = "<5"
            rate = "<5"
            interval = "<5"
        else:
            count = str(int(row.count))
            rate = f"{row.rate_per_100k:.2f}"
            interval = f"{row.rate_ci_lower_per_100k:.2f}–{row.rate_ci_upper_per_100k:.2f}"
        rows.append(
            f"| {row.geography} | {row.outcome_id} | {row.age_group} | {row.sex} | "
            f"{count} | {rate} | {interval} |"
        )
    lines = [
        "# Taxas específicas de mortalidade por idade e sexo — SIM 2022",
        "",
        f"Execução: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "A taxa é óbitos de residentes pela causa básica / população residente do "
        "mesmo grupo etário e sexo × 100.000. O IC 95% é exato de Poisson. "
        "Esta é uma taxa específica bruta de 2022, não uma taxa padronizada.",
        "",
        "- Denominador: Censo 2022, SIDRA 9514.",
        "- Comparador: restante do RJ excluindo Volta Redonda.",
        "- Células menores que cinco suprimem contagem, taxa e intervalo.",
        "- 2022 permanece período de interrupção assistencial para câncer; não é comparado automaticamente como linha de base normal.",
        "",
        "## Resultados selecionados",
        "",
        "| território | desfecho | idade | sexo | óbitos | taxa/100 mil | IC 95%/100 mil |",
        "|---|---|---|---|---:|---:|---:|",
        *rows,
        "",
        "A padronização direta e comparações temporais específicas exigem o mesmo "
        "padrão etário e denominadores compatíveis em todos os anos. Nenhuma "
        "associação causal com poluição ou CSN é estimada.",
    ]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_age_sex_rates(root: Path) -> tuple[Path, Path, Path]:
    rates, counts_path, denominator_path = _build_rates(root)
    output = root / "data" / "processed" / "sim_mortality_age_sex_rates_2022.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    rates.to_parquet(output, index=False)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "validated_sim_2022_specific_crude_rates_no_standardization",
        "year": YEAR,
        "rows": int(len(rates)),
        "outcome_ids": sorted(rates["outcome_id"].unique().tolist()),
        "geographies": sorted(rates["geography"].unique().tolist()),
        "age_groups": AGE_GROUPS,
        "sexes": SEXES,
        "output_path": str(output.relative_to(root)),
        "output_sha256": sha256_file(output),
        "input_files": [
            {"path": str(counts_path.relative_to(root)), "sha256": sha256_file(counts_path)},
            {"path": str(denominator_path.relative_to(root)), "sha256": sha256_file(denominator_path)},
        ],
        "rules": {
            "rate": "deaths divided by same age-sex resident population times 100,000",
            "interval": "exact Poisson 95% interval",
            "comparison": "Volta Redonda versus rest of RJ excluding VR",
        },
        "notes": [
            "Rates are specific crude rates for 2022 and are not age-standardized.",
            "Only age and sex groups with official Censo denominators are included.",
            "Small cells are suppressed in the technical report.",
            "No causal inference or incidence estimate is produced.",
        ],
    }
    manifest_path = root / "reports" / "quality" / "sim_age_sex_rates_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = _write_report(root, rates)
    return output, manifest_path, report_path
