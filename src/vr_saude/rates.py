from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from scipy.stats import chi2, norm

from .provenance import sha256_file


RATE_MULTIPLIER = 100_000
ALPHA = 0.05


def poisson_count_interval(count: int, alpha: float = ALPHA) -> tuple[float, float]:
    if count < 0:
        raise ValueError("count cannot be negative")
    lower = 0.0 if count == 0 else 0.5 * float(chi2.ppf(alpha / 2, 2 * count))
    upper = 0.5 * float(chi2.ppf(1 - alpha / 2, 2 * (count + 1)))
    return lower, upper


def _load_morbidity(root: Path) -> tuple[pd.DataFrame, list[Path]]:
    paths = sorted((root / "data" / "interim").glob("sih_morbidity_*.csv"))
    if not paths:
        raise FileNotFoundError("no SIH morbidity CSV found")
    data = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
    keys = ["year", "month", "geography", "outcome_id"]
    duplicates = int(data.duplicated(keys).sum())
    data = data.sort_values(keys).drop_duplicates(keys, keep="last")
    data["year"] = pd.to_numeric(data["year"], errors="raise").astype(int)
    data["month"] = pd.to_numeric(data["month"], errors="raise").astype(int)
    data["value"] = pd.to_numeric(data["value"], errors="raise").astype(int)
    if (data["value"] < 0).any():
        raise ValueError("SIH morbidity contains negative values")
    data.attrs["duplicate_rows_removed"] = duplicates
    return data, paths


def _load_denominators(root: Path) -> pd.DataFrame:
    path = root / "data" / "processed" / "population_denominators.parquet"
    if not path.exists():
        raise FileNotFoundError(f"population denominator Parquet is missing: {path}")
    data = pd.read_parquet(path)
    data["year"] = pd.to_numeric(data["year"], errors="raise").astype(int)
    data["population"] = pd.to_numeric(data["population"], errors="raise").astype(int)
    return data


def _rate_ratio_interval(count_vr: int, count_rest: int, alpha: float = ALPHA) -> tuple[float | None, float | None]:
    if count_vr <= 0 or count_rest <= 0:
        return None, None
    ratio = count_vr / count_rest
    z = float(norm.ppf(1 - alpha / 2))
    standard_error = math.sqrt(1 / count_vr + 1 / count_rest)
    return math.exp(math.log(ratio) - z * standard_error), math.exp(math.log(ratio) + z * standard_error)


def _annual_rate_frame(root: Path) -> tuple[pd.DataFrame, dict[str, object], list[Path]]:
    morbidity, input_paths = _load_morbidity(root)
    denominator = _load_denominators(root)
    month_counts = morbidity.groupby("year")["month"].nunique().to_dict()
    complete_sih_years = sorted(year for year, count in month_counts.items() if count == 12)
    partial_sih_years = sorted(year for year, count in month_counts.items() if count != 12)
    denominator_years = set(denominator["year"].unique().tolist())
    missing_denominator_years = sorted(year for year in complete_sih_years if year not in denominator_years)
    eligible_years = sorted(year for year in complete_sih_years if year in denominator_years)
    eligible_morbidity = morbidity.loc[morbidity["year"].isin(eligible_years)].copy()
    counts = (
        eligible_morbidity.groupby(["year", "geography", "outcome_id", "outcome_label"], as_index=False)["value"]
        .sum()
        .rename(columns={"value": "count"})
    )
    denominator = denominator.rename(columns={"population": "denominator"})
    counts = counts.merge(
        denominator[["year", "geography", "denominator", "source_status"]],
        on=["year", "geography"],
        how="left",
        validate="many_to_one",
    )
    if counts["denominator"].isna().any():
        raise ValueError("eligible SIH year has no denominator for one geography")
    lower_counts: list[float] = []
    upper_counts: list[float] = []
    for count in counts["count"].astype(int):
        lower, upper = poisson_count_interval(count)
        lower_counts.append(lower)
        upper_counts.append(upper)
    counts["rate_per_100k"] = counts["count"] / counts["denominator"] * RATE_MULTIPLIER
    counts["rate_ci_lower_per_100k"] = [value / pop * RATE_MULTIPLIER for value, pop in zip(lower_counts, counts["denominator"])]
    counts["rate_ci_upper_per_100k"] = [value / pop * RATE_MULTIPLIER for value, pop in zip(upper_counts, counts["denominator"])]
    counts["period_status"] = counts["year"].map(lambda year: "provisional_2025" if year == 2025 else "complete_annual")
    comparison = counts.pivot_table(
        index=["year", "outcome_id"],
        columns="geography",
        values=["count", "rate_per_100k"],
        aggfunc="first",
    )
    comparison.columns = ["_".join(column).strip() for column in comparison.columns.to_flat_index()]
    comparison = comparison.reset_index()
    counts = counts.merge(comparison, on=["year", "outcome_id"], how="left", validate="many_to_one")
    counts["rate_ratio_vr_vs_rest"] = counts["rate_per_100k_volta_redonda"] / counts["rate_per_100k_rest_of_rj_excluding_vr"]
    counts["rate_difference_vr_minus_rest_per_100k"] = counts["rate_per_100k_volta_redonda"] - counts["rate_per_100k_rest_of_rj_excluding_vr"]
    ratio_intervals = [
        _rate_ratio_interval(int(vr), int(rest))
        for vr, rest in zip(counts["count_volta_redonda"], counts["count_rest_of_rj_excluding_vr"])
    ]
    counts["rate_ratio_ci_lower"] = [interval[0] for interval in ratio_intervals]
    counts["rate_ratio_ci_upper"] = [interval[1] for interval in ratio_intervals]
    counts = counts.sort_values(["year", "outcome_id", "geography"]).reset_index(drop=True)
    metadata = {
        "duplicate_rows_removed_from_input": int(morbidity.attrs["duplicate_rows_removed"]),
        "month_count_by_year": {str(year): int(count) for year, count in sorted(month_counts.items())},
        "complete_sih_years": complete_sih_years,
        "partial_sih_years": partial_sih_years,
        "missing_denominator_years": missing_denominator_years,
        "eligible_years": eligible_years,
    }
    return counts, metadata, input_paths


def _write_rate_report(root: Path, rates: pd.DataFrame, metadata: dict[str, object], input_paths: list[Path]) -> Path:
    report = root / "reports" / "technical" / "taxas_respiratorias.md"
    primary = rates.loc[
        (rates["outcome_id"] == "resp_all")
        & (rates["geography"].isin(["volta_redonda", "rest_of_rj_excluding_vr"]))
    ].copy()
    rows = []
    for row in primary.itertuples(index=False):
        values = row._asdict()
        rows.append(
            f"| {values['year']} | {values['geography']} | {int(values['count'])} | "
            f"{values['rate_per_100k']:.2f} | {values['rate_ci_lower_per_100k']:.2f}–{values['rate_ci_upper_per_100k']:.2f} |"
        )
    lines = [
        "# Taxas respiratórias brutas",
        "",
        f"Execução: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "A taxa é calculada como internações agregadas do SIH / população residente × 100.000. "
        "O intervalo é exato de Poisson para a contagem. A razão compara a taxa de VR com a do "
        "restante do RJ, que exclui o código IBGE 3306305.",
        "",
        f"- Anos elegíveis: **{metadata['eligible_years']}**.",
        f"- Anos SIH parciais excluídos da taxa anual: **{metadata['partial_sih_years']}**.",
        f"- Anos completos sem denominador excluídos: **{metadata['missing_denominator_years']}**.",
        f"- Linhas duplicadas removidas ao combinar as janelas SIH: **{metadata['duplicate_rows_removed_from_input']}**.",
        "- 2025 é marcado como provisório; 2026-01 a 2026-05 não é anualizado.",
        "",
        "## Desfecho primário: todas as doenças respiratórias",
        "",
        "| ano | território | internações | taxa/100 mil | IC 95%/100 mil |",
        "|---:|---|---:|---:|---:|",
        *rows,
        "",
        "As taxas por pneumonia, bronquite/bronquiolite aguda, DPOC, asma e pneumoconiose "
        "estão no Parquet processado. Células pequenas devem ser suprimidas ou agregadas "
        "antes de qualquer publicação; este relatório não publica tabelas anuais desses "
        "subgrupos raros.",
        "",
        "## Fontes intermediárias",
        "",
        *[f"- `{path.relative_to(root)}` — SHA-256 `{sha256_file(path)}`" for path in input_paths],
        "",
        "Não há ajuste por idade, sexo, sazonalidade, pandemia ou poluição nesta etapa. "
        "Uma taxa bruta não sustenta comparação causal nem substitui a padronização etária.",
    ]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_respiratory_rates(root: Path) -> tuple[Path, Path, Path]:
    rates, metadata, input_paths = _annual_rate_frame(root)
    output_dir = root / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "respiratory_rates_annual.parquet"
    rates.to_parquet(output, index=False)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "validated_crude_rates_with_poisson_ci_no_age_standardization",
        **metadata,
        "rows": int(len(rates)),
        "output_path": str(output.relative_to(root)),
        "output_sha256": sha256_file(output),
        "input_paths": [
            {"path": str(path.relative_to(root)), "sha256": sha256_file(path)}
            for path in input_paths
        ],
        "notes": [
            "Rates use annual SIH counts only when all 12 months are present.",
            "Population denominator is the aggregated annual denominator by geography.",
            "2025 is provisional; 2026 partial months are excluded from annual rates.",
            "No age/sex standardization, seasonality, interruption model, or causal analysis is performed.",
            "Small cells require suppression or aggregation before publication.",
        ],
    }
    manifest_path = root / "reports" / "quality" / "respiratory_rates_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = _write_rate_report(root, rates, metadata, input_paths)
    return output, manifest_path, report_path
