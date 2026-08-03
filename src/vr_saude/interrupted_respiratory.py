from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm

from .provenance import sha256_file


RESPIRATORY_OUTCOMES = [
    "resp_all",
    "pneumonia",
    "acute_bronchitis_bronchiolitis",
    "copd",
    "asthma",
    "pneumoconiosis",
]
MODEL_GEOGRAPHIES = ["volta_redonda", "rest_of_rj_excluding_vr"]
PANDEMIC_START = pd.Timestamp("2020-03-01")
MAX_COMPLETE_YEAR = 2025
RATE_MULTIPLIER = 100_000
ALPHA = 0.05


def _load_monthly_inputs(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, list[Path]]:
    input_paths = sorted((root / "data" / "interim").glob("sih_morbidity_*.csv"))
    if not input_paths:
        raise FileNotFoundError("no SIH morbidity interim CSV was found")
    morbidity = pd.concat([pd.read_csv(path) for path in input_paths], ignore_index=True)
    keys = ["year", "month", "geography", "outcome_id"]
    duplicates = int(morbidity.duplicated(keys).sum())
    morbidity = morbidity.sort_values(keys).drop_duplicates(keys, keep="last")
    morbidity["year"] = pd.to_numeric(morbidity["year"], errors="raise").astype(int)
    morbidity["month"] = pd.to_numeric(morbidity["month"], errors="raise").astype(int)
    morbidity["count"] = pd.to_numeric(morbidity["value"], errors="raise").astype(int)
    if (morbidity["count"] < 0).any():
        raise ValueError("SIH morbidity contains negative counts")
    morbidity = morbidity.loc[
        morbidity["outcome_id"].isin(RESPIRATORY_OUTCOMES)
        & morbidity["geography"].isin(MODEL_GEOGRAPHIES)
    ].copy()
    morbidity["period"] = pd.to_datetime(
        morbidity["year"].astype(str) + "-" + morbidity["month"].astype(str).str.zfill(2) + "-01"
    )
    denominator_path = root / "data" / "processed" / "population_denominators.parquet"
    if not denominator_path.exists():
        raise FileNotFoundError(f"population denominator Parquet is missing: {denominator_path}")
    denominator = pd.read_parquet(denominator_path)
    denominator["year"] = pd.to_numeric(denominator["year"], errors="raise").astype(int)
    denominator["population"] = pd.to_numeric(denominator["population"], errors="raise").astype(int)
    denominator = denominator.loc[denominator["geography"].isin(MODEL_GEOGRAPHIES)].copy()
    morbidity.attrs["duplicate_rows_removed"] = duplicates
    return morbidity, denominator, input_paths


def _add_interruption_variables(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["time_index"] = (
        (result["period"].dt.year - 2008) * 12 + result["period"].dt.month - 1
    ).astype(int)
    break_index = (PANDEMIC_START.year - 2008) * 12 + PANDEMIC_START.month - 1
    result["pandemic_step"] = result["period"].ge(PANDEMIC_START).astype(int)
    result["post_pandemic_time"] = (result["time_index"] - break_index).clip(lower=0)
    result["monthly_population"] = result["population"] / 12
    result["offset_log_population"] = result["monthly_population"].map(math.log)
    result["period_status"] = result["year"].map(
        lambda year: "provisional_2025" if year == 2025 else "eligible_complete_year"
    )
    return result


def _model_input(root: Path) -> tuple[pd.DataFrame, dict[str, object], list[Path]]:
    morbidity, denominator, input_paths = _load_monthly_inputs(root)
    month_counts = morbidity.groupby("year")["month"].nunique().to_dict()
    complete_sih_years = sorted(
        int(year) for year, count in month_counts.items() if count == 12 and int(year) <= MAX_COMPLETE_YEAR
    )
    partial_sih_years = sorted(int(year) for year, count in month_counts.items() if count != 12)
    denominator_years = set(int(year) for year in denominator["year"].unique())
    missing_denominator_years = sorted(year for year in complete_sih_years if year not in denominator_years)
    eligible_years = sorted(year for year in complete_sih_years if year in denominator_years)
    data = morbidity.loc[morbidity["year"].isin(eligible_years)].copy()
    data = data.merge(
        denominator[["year", "geography", "population", "source_status"]],
        on=["year", "geography"],
        how="left",
        validate="many_to_one",
    )
    if data.empty or data["population"].isna().any():
        raise ValueError("eligible SIH months have no compatible population denominator")
    data = _add_interruption_variables(data)
    data = data.sort_values(["outcome_id", "geography", "period"]).reset_index(drop=True)
    metadata = {
        "duplicate_rows_removed_from_input": int(morbidity.attrs["duplicate_rows_removed"]),
        "month_count_by_year": {str(year): int(count) for year, count in sorted(month_counts.items())},
        "complete_sih_years": complete_sih_years,
        "partial_sih_years": partial_sih_years,
        "missing_denominator_years": missing_denominator_years,
        "eligible_years": eligible_years,
        "pandemic_start": PANDEMIC_START.strftime("%Y-%m"),
    }
    return data, metadata, input_paths


def _design_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    design = frame[["time_index", "pandemic_step", "post_pandemic_time"]].astype(float)
    month_dummies = pd.get_dummies(frame["month"], prefix="month", drop_first=True, dtype=float)
    design = pd.concat([pd.Series(1.0, index=frame.index, name="const"), design, month_dummies], axis=1)
    return design.astype(float)


def _coefficient_summary(
    fit: sm.GLM,
    design: pd.DataFrame,
    weights: dict[str, float],
) -> tuple[float, float, float, float]:
    params = pd.Series(fit.params, index=design.columns)
    covariance = pd.DataFrame(fit.cov_params(), index=design.columns, columns=design.columns)
    vector = pd.Series(0.0, index=design.columns)
    for name, weight in weights.items():
        vector[name] = weight
    estimate = float(vector.dot(params))
    variance = float(vector.dot(covariance).dot(vector))
    standard_error = math.sqrt(max(variance, 0.0))
    z = float(norm.ppf(1 - ALPHA / 2))
    lower = estimate - z * standard_error
    upper = estimate + z * standard_error
    p_value = 1.0 if standard_error == 0 else float(2 * norm.sf(abs(estimate / standard_error)))
    return math.exp(estimate), math.exp(lower), math.exp(upper), p_value


def _fit_one(frame: pd.DataFrame) -> dict[str, object]:
    design = _design_matrix(frame)
    counts = frame["count"].astype(float)
    model = sm.GLM(
        counts,
        design,
        family=sm.families.Poisson(),
        offset=frame["offset_log_population"],
    )
    covariance_type = "HAC_12"
    try:
        fit = model.fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    except (TypeError, ValueError, np.linalg.LinAlgError):
        fit = model.fit(cov_type="HC0")
        covariance_type = "HC0"
    estimates = {
        "baseline_trend_rr_per_month": {"time_index": 1.0},
        "immediate_level_rr": {"pandemic_step": 1.0},
        "post_slope_change_rr_per_month": {"post_pandemic_time": 1.0},
        "post_trend_rr_per_month": {"time_index": 1.0, "post_pandemic_time": 1.0},
    }
    result: dict[str, object] = {
        "outcome_id": str(frame["outcome_id"].iloc[0]),
        "outcome_label": str(frame["outcome_label"].iloc[0]),
        "geography": str(frame["geography"].iloc[0]),
        "n_obs": int(len(frame)),
        "total_events": int(frame["count"].sum()),
        "covariance": covariance_type,
        "pearson_dispersion": float(fit.pearson_chi2 / fit.df_resid),
        "aic": float(fit.aic),
    }
    for prefix, weights in estimates.items():
        estimate, lower, upper, p_value = _coefficient_summary(fit, design, weights)
        result[prefix] = estimate
        result[f"{prefix}_ci_lower"] = lower
        result[f"{prefix}_ci_upper"] = upper
        result[f"{prefix}_p_value"] = p_value
    return result


def _fit_models(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (outcome_id, geography), group in data.groupby(["outcome_id", "geography"], sort=True):
        if len(group) < 24 or int(group["count"].sum()) < 5:
            rows.append(
                {
                    "outcome_id": outcome_id,
                    "outcome_label": group["outcome_label"].iloc[0],
                    "geography": geography,
                    "n_obs": int(len(group)),
                    "total_events": int(group["count"].sum()),
                    "model_status": "suppressed_insufficient_events",
                }
            )
            continue
        result = _fit_one(group)
        result["model_status"] = "fitted_descriptive_its"
        rows.append(result)
    return pd.DataFrame(rows).sort_values(["outcome_id", "geography"]).reset_index(drop=True)


def _format_rr(row: pd.Series, prefix: str) -> str:
    value = row.get(prefix)
    lower = row.get(f"{prefix}_ci_lower")
    upper = row.get(f"{prefix}_ci_upper")
    if pd.isna(value) or pd.isna(lower) or pd.isna(upper):
        return "suprimido"
    return f"{value:.3f} ({lower:.3f}–{upper:.3f})"


def _write_report(root: Path, models: pd.DataFrame, metadata: dict[str, object], input_paths: list[Path]) -> Path:
    report = root / "reports" / "technical" / "serie_interrompida_respiratoria.md"
    rows = []
    for row in models.itertuples(index=False):
        row_data = pd.Series(row._asdict())
        if row.model_status != "fitted_descriptive_its":
            continue
        rows.append(
            f"| {row.geography} | {row.outcome_id} | {int(row.total_events)} | "
            f"{_format_rr(row_data, 'baseline_trend_rr_per_month')} | "
            f"{_format_rr(row_data, 'immediate_level_rr')} | "
            f"{_format_rr(row_data, 'post_trend_rr_per_month')} |"
        )
    lines = [
        "# Série temporal interrompida — internações respiratórias do SIH",
        "",
        f"Execução: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "O modelo usa contagens mensais de internações/AIH de residentes, com offset "
        "da população anual dividida por 12, indicadores de março de 2020 e tendência "
        "pós-intervenção, além de indicadores mensais de sazonalidade. Os intervalos "
        "usam covariância robusta HAC com 12 defasagens quando disponível.",
        "",
        "A razão de tendência é multiplicativa por mês. A razão de nível imediato compara "
        "o salto estimado em março de 2020 com o contrafactual da tendência pré-pandemia. "
        "Isto é uma análise temporal descritiva/associativa: não estima efeito causal da "
        "pandemia, de poluentes ou da CSN.",
        "",
        f"- Ruptura definida a priori: **{metadata['pandemic_start']}**.",
        f"- Anos completos no SIH: **{metadata['complete_sih_years']}**.",
        f"- Anos elegíveis no modelo: **{metadata['eligible_years']}**.",
        f"- Anos completos sem denominador e excluídos: **{metadata['missing_denominator_years']}**.",
        f"- Anos parciais e excluídos: **{metadata['partial_sih_years']}**.",
        "- 2025 é provisório; 2026-01 a 2026-05 não é anualizado nem modelado.",
        "- SIH conta AIH/internações agregadas, não pessoas únicas nem casos novos.",
        "",
        "## Resultados dos modelos",
        "",
        "Células com menos de cinco eventos totais não são publicadas. As estimativas "
        "abaixo devem ser interpretadas junto com a dispersão, cobertura temporal e "
        "mudanças assistenciais.",
        "",
        "| território | desfecho | eventos | tendência pré/mês | nível em mar-2020 | tendência pós/mês |",
        "|---|---|---:|---:|---:|---:|",
        *rows,
        "",
        "## Proveniência",
        "",
        *[f"- `{path.relative_to(root)}` — SHA-256 `{sha256_file(path)}`" for path in input_paths],
        "",
        "A ausência de dados de idade/sexo no SIH impede taxas específicas neste produto; "
        "as taxas específicas SIM 2022 são um produto separado. Nenhuma associação "
        "ecológica é atribuída à CSN.",
    ]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_interrupted_respiratory(root: Path) -> tuple[Path, Path, Path]:
    data, metadata, input_paths = _model_input(root)
    models = _fit_models(data)
    output = root / "data" / "processed" / "sih_respiratory_interrupted_series.parquet"
    model_output = root / "data" / "processed" / "sih_respiratory_interrupted_models.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_parquet(output, index=False)
    models.to_parquet(model_output, index=False)
    report = _write_report(root, models, metadata, input_paths)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "descriptive_interrupted_time_series_no_causal_inference",
        **metadata,
        "model_rows": int(len(models)),
        "fitted_models": int((models["model_status"] == "fitted_descriptive_its").sum()),
        "suppressed_models": int((models["model_status"] != "fitted_descriptive_its").sum()),
        "output_path": str(output.relative_to(root)),
        "output_sha256": sha256_file(output),
        "model_output_path": str(model_output.relative_to(root)),
        "model_output_sha256": sha256_file(model_output),
        "report_path": str(report.relative_to(root)),
        "input_paths": [
            {"path": str(path.relative_to(root)), "sha256": sha256_file(path)}
            for path in input_paths
        ],
        "model": {
            "family": "Poisson GLM",
            "offset": "log(annual resident population / 12)",
            "terms": ["time_index", "pandemic_step", "post_pandemic_time", "month indicators"],
            "covariance": "HAC maxlags=12 with HC0 fallback",
        },
        "notes": [
            "SIH observations are aggregated AIH events and not unique persons.",
            "2020-03 is a pre-specified respiratory pandemic break.",
            "Missing denominator years are excluded rather than interpolated.",
            "This model is descriptive/associative and does not estimate causality.",
        ],
    }
    manifest_path = root / "reports" / "quality" / "respiratory_its_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output, manifest_path, report
