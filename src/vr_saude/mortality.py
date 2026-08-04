from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from .config import load_config
from .provenance import sha256_file
from .rates import RATE_MULTIPLIER, _rate_ratio_interval, poisson_count_interval


GEOGRAPHIES = ["brazil_total", "rj_total", "volta_redonda", "rest_of_rj_excluding_vr"]
ALPHA = 0.05


def _outcome_sections(root: Path) -> dict[str, set[str]]:
    config = load_config("outcomes.yml", root)
    return {
        section: {
            item["id"] for item in config.get(section, []) if "SIM" in item.get("source", [])
        }
        for section in ("respiratory", "cardiovascular", "cardiorespiratory", "cancer", "neurological")
    }


def period_status(root: Path, year: int, outcome_id: str) -> str:
    sections = _outcome_sections(root)
    respiratory = sections["respiratory"]
    cardiovascular = sections["cardiovascular"]
    cardiorespiratory = sections["cardiorespiratory"]
    cancer = sections["cancer"]
    neurological = sections["neurological"]
    if outcome_id in cancer:
        if 2020 <= year <= 2022:
            return "cancer_care_disruption"
        if year >= 2025:
            return "cancer_provisional_prevenir_50_plus"
    if outcome_id in respiratory:
        if 2020 <= year <= 2021:
            return "respiratory_pandemic"
        if year >= 2025:
            return "respiratory_provisional"
    if outcome_id in cardiovascular:
        if 2020 <= year <= 2021:
            return "cardiovascular_pandemic_context"
        if year >= 2025:
            return "cardiovascular_provisional"
    if outcome_id in cardiorespiratory:
        if 2020 <= year <= 2021:
            return "cardiorespiratory_pandemic_context"
        if year >= 2025:
            return "cardiorespiratory_provisional"
    if outcome_id in neurological and year >= 2025:
        return "neurological_provisional"
    return "source_year_observed"


def _load_inputs(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, Path, Path]:
    counts_path = root / "data" / "processed" / "outcome_counts_sim_sivep.parquet"
    population_path = root / "data" / "processed" / "population_denominators.parquet"
    if not counts_path.exists():
        raise FileNotFoundError(f"outcome counts Parquet is missing: {counts_path}")
    if not population_path.exists():
        raise FileNotFoundError(f"population denominator Parquet is missing: {population_path}")
    counts = pd.read_parquet(counts_path)
    population = pd.read_parquet(population_path)
    counts = counts.loc[counts["source"] == "SIM"].copy()
    if counts.empty:
        raise ValueError("no SIM outcome counts available")
    counts["source_year"] = pd.to_numeric(counts["source_year"], errors="raise").astype(int)
    counts["count"] = pd.to_numeric(counts["count"], errors="raise").astype(int)
    if (counts["count"] < 0).any():
        raise ValueError("SIM outcome counts contain negative values")
    population["year"] = pd.to_numeric(population["year"], errors="raise").astype(int)
    population["population"] = pd.to_numeric(population["population"], errors="raise").astype(int)
    return counts, population, counts_path, population_path


def _complete_geography_grid(counts: pd.DataFrame) -> pd.DataFrame:
    observed = counts.groupby(
        ["source_year", "outcome_id", "outcome_label"], as_index=False
    )["count"].sum()
    years_outcomes = observed[["source_year", "outcome_id", "outcome_label"]].drop_duplicates()
    geographies = pd.DataFrame({"geography": GEOGRAPHIES})
    grid = years_outcomes.merge(geographies, how="cross")
    totals = counts.groupby(
        ["source_year", "geography", "outcome_id", "outcome_label"], as_index=False
    )["count"].sum()
    grid = grid.merge(
        totals,
        on=["source_year", "geography", "outcome_id", "outcome_label"],
        how="left",
        validate="one_to_one",
    )
    grid["count"] = grid["count"].fillna(0).astype(int)
    return grid


def _build_rates(root: Path) -> tuple[pd.DataFrame, dict[str, object], Path, Path]:
    counts, population, counts_path, population_path = _load_inputs(root)
    counts = _complete_geography_grid(counts)
    observed_years = sorted(counts["source_year"].unique().tolist())
    denominator_years = set(population["year"].unique().tolist())
    missing_denominator_years = sorted(set(observed_years) - denominator_years)
    counts = counts.loc[counts["source_year"].isin(denominator_years)].copy()
    if counts.empty:
        raise ValueError("no SIM years have population denominators")
    counts = counts.merge(
        population[["year", "geography", "population", "source_status"]].rename(columns={"year": "source_year"}),
        on=["source_year", "geography"],
        how="left",
        validate="many_to_one",
    )
    if counts["population"].isna().any():
        missing = sorted(counts.loc[counts["population"].isna(), "source_year"].unique().tolist())
        raise ValueError(f"SIM eligible years without population denominators: {missing}")
    counts["population"] = counts["population"].astype(int)
    lower_counts: list[float] = []
    upper_counts: list[float] = []
    for count in counts["count"]:
        lower, upper = poisson_count_interval(int(count))
        lower_counts.append(lower)
        upper_counts.append(upper)
    counts["rate_per_100k"] = counts["count"] / counts["population"] * RATE_MULTIPLIER
    counts["rate_ci_lower_per_100k"] = [
        value / population_value * RATE_MULTIPLIER
        for value, population_value in zip(lower_counts, counts["population"])
    ]
    counts["rate_ci_upper_per_100k"] = [
        value / population_value * RATE_MULTIPLIER
        for value, population_value in zip(upper_counts, counts["population"])
    ]
    counts["period_status"] = [
        period_status(root, int(year), outcome_id)
        for year, outcome_id in zip(counts["source_year"], counts["outcome_id"])
    ]
    comparison = counts.pivot_table(
        index=["source_year", "outcome_id"],
        columns="geography",
        values=["count", "rate_per_100k", "population"],
        aggfunc="first",
    )
    comparison.columns = ["_".join(column).strip() for column in comparison.columns.to_flat_index()]
    comparison = comparison.reset_index()
    counts = counts.merge(comparison, on=["source_year", "outcome_id"], how="left", validate="many_to_one")
    counts["rate_ratio_vr_vs_rest"] = (
        counts["rate_per_100k_volta_redonda"] / counts["rate_per_100k_rest_of_rj_excluding_vr"]
    )
    counts["rate_difference_vr_minus_rest_per_100k"] = (
        counts["rate_per_100k_volta_redonda"] - counts["rate_per_100k_rest_of_rj_excluding_vr"]
    )
    intervals = [
        _rate_ratio_interval(int(vr), int(rest), pop_vr, pop_rest)
        for vr, rest, pop_vr, pop_rest in zip(
            counts["count_volta_redonda"],
            counts["count_rest_of_rj_excluding_vr"],
            counts["population_volta_redonda"],
            counts["population_rest_of_rj_excluding_vr"],
        )
    ]
    counts["rate_ratio_ci_lower"] = [interval[0] for interval in intervals]
    counts["rate_ratio_ci_upper"] = [interval[1] for interval in intervals]
    counts = counts.rename(columns={"source_year": "year", "source_status": "population_source_status"})
    counts = counts.sort_values(["year", "outcome_id", "geography"]).reset_index(drop=True)
    metadata = {
        "observed_years": observed_years,
        "available_years": sorted(counts["year"].unique().tolist()),
        "missing_denominator_years": missing_denominator_years,
        "outcome_ids": sorted(counts["outcome_id"].unique().tolist()),
        "coverage_status": "annual_sim_source_years_observed_2010_2024_rates_limited_by_denominator",
        "missing_source_years_between_2010_2024": sorted(set(range(2010, 2025)) - set(observed_years)),
        "missing_rate_years_between_2010_2024": sorted(set(range(2010, 2025)) - set(counts["year"].unique())),
    }
    return counts, metadata, counts_path, population_path


def _write_report(root: Path, rates: pd.DataFrame, metadata: dict[str, object]) -> Path:
    report = root / "reports" / "technical" / "mortalidade_sim.md"
    displayed_outcomes = [
        "all_malignant_neoplasms",
        "resp_all",
        "lung",
        "bladder",
        "non_hodgkin_lymphoma",
        "multiple_myeloma",
        "leukemia",
        "colorectal",
    ]
    selected = rates.loc[
        rates["outcome_id"].isin(displayed_outcomes)
        & rates["geography"].isin(["volta_redonda", "rest_of_rj_excluding_vr"])
    ].copy()
    rows = []
    for row in selected.sort_values(["year", "outcome_id", "geography"]).itertuples(index=False):
        if row.count < 5:
            count = "<5"
            rate = "<5"
            interval = "<5"
        else:
            count = str(int(row.count))
            rate = f"{row.rate_per_100k:.2f}"
            interval = f"{row.rate_ci_lower_per_100k:.2f}–{row.rate_ci_upper_per_100k:.2f}"
        rows.append(
            f"| {row.year} | {row.geography} | {row.outcome_id} | {count} | {rate} | {interval} | {row.period_status} |"
        )
    lines = [
        "# Mortalidade por causas selecionadas no SIM",
        "",
        f"Execução: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "A contagem representa óbitos de residentes classificados pela causa básica. "
        "A taxa é óbitos/população residente × 100.000, com intervalo exato de Poisson. "
        "Isso não mede incidência de câncer nem risco etiológico.",
        "",
        f"- Anos observados nos arquivos SIM: **{metadata['observed_years']}**.",
        f"- Anos elegíveis para taxa após o denominador: **{metadata['available_years']}**.",
        f"- Anos observados sem denominador, excluídos sem interpolação: **{metadata['missing_denominator_years']}**.",
        f"- Anos sem taxa entre 2010 e 2024, sem interpolação: **{metadata['missing_rate_years_between_2010_2024']}**.",
        "- Os arquivos SIM cobrem todos os anos de 2010 a 2024 nesta execução; 2010 usa o Censo 2010 e 2023 permanece sem denominador populacional compatível.",
        "- 2020 é marcado como interrupção assistencial para câncer e período pandêmico para causas respiratórias.",
        "- Células menores que cinco suprimem contagem, taxa e intervalo nesta apresentação.",
        "",
        "## Taxas brutas",
        "",
        "| ano | território | desfecho | óbitos | taxa/100 mil | IC 95%/100 mil | período |",
        "|---:|---|---|---:|---:|---:|---|",
        *rows,
        "",
        "O arquivo processado também contém os demais desfechos definidos em "
        "`config/outcomes.yml`, além da razão de taxas de Volta Redonda versus o restante "
        "do RJ. Nenhuma associação com poluição ou CSN é estimada nesta etapa.",
        "",
        "## Limitações",
        "",
        "- Os arquivos SIM de 2010–2024 foram adquiridos e harmonizados; o status definitivo/preliminar de cada recurso permanece uma dimensão de proveniência e não é misturado automaticamente.",
        "- Esta camada não faz padronização, causas múltiplas, mortalidade prematura ou "
        "anos potenciais de vida perdidos; taxas específicas SIM 2022 estão em produto separado.",
        "- 2020–2022 deve ser interpretado à luz da interrupção assistencial oncológica; não é uma linha de base normal.",
        "- O comparador exclui Volta Redonda por residência e não autoriza inferência causal.",
    ]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_mortality_rates(root: Path) -> tuple[Path, Path, Path]:
    rates, metadata, counts_path, population_path = _build_rates(root)
    output = root / "data" / "processed" / "sim_mortality_rates_sample.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    rates.to_parquet(output, index=False)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "sampled_sim_crude_mortality_rates_no_incidence_estimate",
        **metadata,
        "rows": int(len(rates)),
        "output_path": str(output.relative_to(root)),
        "output_sha256": sha256_file(output),
        "input_files": [
            {"path": str(path.relative_to(root)), "sha256": sha256_file(path)}
            for path in [counts_path, population_path]
        ],
        "rules": {
            "outcome": "SIM underlying cause classified by CID-10 ranges from config/outcomes.yml",
            "territory": "residence code; VR=330630; rest of RJ excludes VR",
            "rate": "deaths divided by annual resident population times 100,000",
            "interval": "exact Poisson 95% interval for the count",
        },
        "notes": [
            "The three available SIM years are not a continuous annual series and are not used for trend inference.",
            "SIM deaths are not incident cancer cases.",
            "Small cells are suppressed in the technical report.",
            "No age standardization, premature mortality, causal inference, or ecological attribution to CSN is produced.",
        ],
    }
    manifest_path = root / "reports" / "quality" / "sim_mortality_rates_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = _write_report(root, rates, metadata)
    return output, manifest_path, report_path
