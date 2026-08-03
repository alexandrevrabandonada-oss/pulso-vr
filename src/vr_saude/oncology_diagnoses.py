from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .provenance import sha256_file


GEOGRAPHIES = ["brazil_total", "volta_redonda", "rest_of_rj_excluding_vr"]
PERIOD_STATUS = {
    **{year: "observed_pre_disruption" for year in range(2013, 2020)},
    **{year: "cancer_care_disruption" for year in range(2020, 2023)},
    2023: "observed_post_disruption",
    2024: "observed_post_disruption",
}
SITE_GROUPS = {
    "mama": {"C50"},
    "colorretal": {"C18", "C19", "C20", "C21"},
    "colo do útero": {"C53"},
    "próstata": {"C61"},
    "hematológicos selecionados": {"C81", "C83", "C88", "C90", "C91", "C92", "C94", "C96"},
    "pulmão": {"C34"},
    "estômago": {"C16"},
}


def _read_tabnet_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, sep=";", encoding="latin1", dtype=str)
    if frame.shape[1] != 2:
        raise ValueError(f"unexpected Painel-Oncologia layout: {path}")
    frame.columns = ["label", "cases"]
    frame["cases"] = pd.to_numeric(frame["cases"], errors="raise").astype(int)
    return frame


def _read_series(path: Path) -> pd.DataFrame:
    frame = _read_tabnet_csv(path)
    frame = frame.loc[frame["label"].str.fullmatch(r"\d{4}")].copy()
    frame["year"] = frame["label"].astype(int)
    return frame[["year", "cases"]].sort_values("year")


def _load_population(root: Path) -> pd.DataFrame:
    path = root / "data" / "processed" / "population_denominators.parquet"
    if not path.exists():
        raise FileNotFoundError(f"population denominator Parquet is missing: {path}")
    population = pd.read_parquet(path)
    population["year"] = pd.to_numeric(population["year"], errors="raise").astype(int)
    population["population"] = pd.to_numeric(population["population"], errors="raise").astype(int)
    return population.loc[population["geography"].isin(GEOGRAPHIES), ["year", "geography", "population", "source_status"]]


def _build_series(root: Path) -> tuple[pd.DataFrame, dict[str, object], list[Path]]:
    brazil_path = root / "data" / "raw" / "painel_oncologia_brasil_2013_2024.csv"
    vr_path = root / "data" / "raw" / "painel_oncologia_vr_2013_2024.csv"
    rj_path = root / "data" / "raw" / "painel_oncologia_rj_2013_2024.csv"
    for path in (brazil_path, vr_path, rj_path):
        if not path.exists():
            raise FileNotFoundError(f"Painel-Oncologia raw CSV is missing: {path}")

    brazil = _read_series(brazil_path).rename(columns={"cases": "count_brazil_total"})
    vr = _read_series(vr_path).rename(columns={"cases": "count_volta_redonda"})
    rj = _read_series(rj_path).rename(columns={"cases": "count_rj_total"})
    series = (
        brazil.merge(vr, on="year", how="outer", validate="one_to_one")
        .merge(rj, on="year", how="outer", validate="one_to_one")
        .sort_values("year")
    )
    series["count_rest_of_rj_excluding_vr"] = series["count_rj_total"] - series["count_volta_redonda"]
    if (series["count_rest_of_rj_excluding_vr"] < 0).any():
        raise ValueError("RJ total is lower than Volta Redonda in Painel-Oncologia series")

    population = _load_population(root)
    rows = []
    for row in series.itertuples(index=False):
        for geography, count in (
            ("brazil_total", row.count_brazil_total),
            ("volta_redonda", row.count_volta_redonda),
            ("rest_of_rj_excluding_vr", row.count_rest_of_rj_excluding_vr),
        ):
            denominator = population.loc[
                (population["year"] == int(row.year)) & (population["geography"] == geography)
            ]
            if len(denominator) > 1:
                raise ValueError(f"duplicate denominator for {row.year}/{geography}")
            population_value = int(denominator.iloc[0]["population"]) if len(denominator) else None
            source_status = str(denominator.iloc[0]["source_status"]) if len(denominator) else "missing"
            rows.append(
                {
                    "year": int(row.year),
                    "geography": geography,
                    "cases": int(count),
                    "population": population_value,
                    "registration_rate_per_100k": (
                        int(count) / population_value * 100_000 if population_value else None
                    ),
                    "population_source_status": source_status,
                    "period_status": PERIOD_STATUS.get(int(row.year), "source_year_observed"),
                }
            )
    rates = pd.DataFrame(rows)
    comparison = rates.pivot(index="year", columns="geography", values="registration_rate_per_100k")
    rates["registration_rate_ratio_vr_vs_rest"] = rates["year"].map(
        (comparison["volta_redonda"] / comparison["rest_of_rj_excluding_vr"]).to_dict()
    )
    rates["registration_rate_ratio_vr_vs_brazil"] = rates["year"].map(
        (comparison["volta_redonda"] / comparison["brazil_total"]).to_dict()
    )
    rates = rates.sort_values(["year", "geography"]).reset_index(drop=True)
    metadata = {
        "years_observed": sorted(rates["year"].unique().tolist()),
        "years_with_denominator": sorted(rates.loc[rates["population"].notna(), "year"].unique().tolist()),
        "years_without_denominator": sorted(rates.loc[rates["population"].isna(), "year"].unique().tolist()),
        "total_cases_brazil_2013_2024": int(brazil["count_brazil_total"].sum()),
        "total_cases_volta_redonda_2013_2024": int(vr["count_volta_redonda"].sum()),
        "total_cases_rj_2013_2024": int(rj["count_rj_total"].sum()),
        "total_cases_rest_of_rj_excluding_vr_2013_2024": int(series["count_rest_of_rj_excluding_vr"].sum()),
        "mean_annual_registration_rate_per_100k": {
            geography: round(float(value), 2)
            for geography, value in rates.groupby("geography")["registration_rate_per_100k"].mean().dropna().items()
        },
    }
    return rates, metadata, [brazil_path, vr_path, rj_path]


def _build_detail(root: Path) -> tuple[pd.DataFrame, Path]:
    path = root / "data" / "raw" / "painel_oncologia_vr_detalhado_2024.csv"
    if not path.exists():
        raise FileNotFoundError(f"Painel-Oncologia detailed raw CSV is missing: {path}")
    detail = _read_tabnet_csv(path).rename(columns={"label": "diagnosis_label"})
    detail = detail.loc[detail["diagnosis_label"].ne("Total")].copy()
    detail["diagnosis_code"] = detail["diagnosis_label"].str.extract(r"^(C\d{2})", expand=False)
    detail["share_pct"] = detail["cases"] / detail["cases"].sum() * 100
    detail = detail.sort_values(["cases", "diagnosis_code"], ascending=[False, True]).reset_index(drop=True)
    return detail, path


def _site_group_summary(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total = int(detail["cases"].sum())
    for label, codes in SITE_GROUPS.items():
        cases = int(detail.loc[detail["diagnosis_code"].isin(codes), "cases"].sum())
        rows.append({"site_group": label, "cases": cases, "share_pct": cases / total * 100})
    return pd.DataFrame(rows).sort_values("cases", ascending=False).reset_index(drop=True)


def _write_report(root: Path, rates: pd.DataFrame, detail: pd.DataFrame, metadata: dict[str, object]) -> Path:
    report = root / "reports" / "technical" / "diagnosticos_painel_oncologia.md"
    brazil = rates.loc[rates["geography"] == "brazil_total"].sort_values("year")
    vr = rates.loc[rates["geography"] == "volta_redonda"].sort_values("year")
    rest = rates.loc[rates["geography"] == "rest_of_rj_excluding_vr"].sort_values("year")
    comparison = (
        vr.merge(rest, on="year", suffixes=("_vr", "_rest"))
        .merge(brazil, on="year", suffixes=("", "_brazil"))
    )
    rows = []
    for row in comparison.itertuples(index=False):
        vr_rate = "—" if pd.isna(row.registration_rate_per_100k_vr) else f"{row.registration_rate_per_100k_vr:.1f}"
        rest_rate = "—" if pd.isna(row.registration_rate_per_100k_rest) else f"{row.registration_rate_per_100k_rest:.1f}"
        brazil_rate = "—" if pd.isna(row.registration_rate_per_100k) else f"{row.registration_rate_per_100k:.1f}"
        ratio = "—" if pd.isna(row.registration_rate_ratio_vr_vs_rest_vr) else f"{row.registration_rate_ratio_vr_vs_rest_vr:.2f}"
        ratio_brazil = "—" if pd.isna(row.registration_rate_ratio_vr_vs_brazil_vr) else f"{row.registration_rate_ratio_vr_vs_brazil_vr:.2f}"
        rows.append(f"| {row.year} | {row.cases_vr} | {row.cases_rest} | {row.cases} | {vr_rate} | {rest_rate} | {brazil_rate} | {ratio} | {ratio_brazil} | {row.period_status_vr} |")
    top = detail.loc[detail["cases"] >= 5].head(12)
    top_rows = [f"| {row.diagnosis_code} | {row.diagnosis_label} | {int(row.cases)} | {row.share_pct:.1f}% |" for row in top.itertuples(index=False)]
    grouped = _site_group_summary(detail)
    grouped_rows = [f"| {row.site_group} | {int(row.cases)} | {row.share_pct:.1f}% |" for row in grouped.itertuples(index=False)]
    lines = [
        "# Diagnósticos registrados no Painel-Oncologia",
        "",
        f"Execução: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "Esta análise conta registros de casos diagnosticados no Painel-Oncologia por município de residência. "
        "O indicador não é tratado como incidência populacional: o painel combina SIA, SIH e SISCAN e depende da cobertura, "
        "do fluxo assistencial e da qualidade do registro.",
        "",
        "- Período: **2013–2024**; categoria: **Neoplasias Malignas (Lei nº 12.732/2012)**.",
        f"- Brasil: **{metadata['total_cases_brazil_2013_2024']:,}** registros no período (formatação pt-BR: ponto como milhar).".replace(",", "."),
        f"- Volta Redonda: **{metadata['total_cases_volta_redonda_2013_2024']:,}** registros no período (formatação pt-BR: ponto como milhar).".replace(",", "."),
        f"- Restante do RJ: **{metadata['total_cases_rest_of_rj_excluding_vr_2013_2024']:,}** registros no período (VR excluída por residência).".replace(",", "."),
        f"- Anos sem denominador populacional no repositório: **{metadata['years_without_denominator']}**; nesses anos, o relatório mantém somente a contagem.",
        f"- Média anual da taxa descritiva nos 11 anos com denominador: **VR {metadata['mean_annual_registration_rate_per_100k']['volta_redonda']:.1f}**, **restante RJ {metadata['mean_annual_registration_rate_per_100k']['rest_of_rj_excluding_vr']:.1f}**, **Brasil {metadata['mean_annual_registration_rate_per_100k']['brazil_total']:.1f} por 100 mil**.",
        "",
        "## Série anual",
        "",
        "Taxa de registro = casos registrados / população residente × 100.000; é uma medida descritiva de registro assistencial, não uma taxa de incidência validada.",
        "",
        "| ano | VR casos | restante RJ casos | Brasil casos | registros/100 mil VR | registros/100 mil restante RJ | registros/100 mil Brasil | razão VR/restante | razão VR/Brasil | contexto |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        *rows,
        "",
        "## Localizações com maior volume em Volta Redonda — 2024",
        "",
        "Células com menos de cinco registros não são destacadas na tabela pública abaixo.",
        "",
        "| CID-10 | localização detalhada | casos | participação dos casos detalhados |",
        "|---|---|---:|---:|",
        *top_rows,
        "",
        "## Grupos analíticos prioritários — 2024",
        "",
        "Agrupamentos operacionais para leitura; eles não alteram a classificação original do Painel-Oncologia.",
        "",
        "| grupo | casos | participação |",
        "|---|---:|---:|",
        *grouped_rows,
        "",
        "## Leitura inicial dos pontos mais impactantes",
        "",
        "- 2024 teve **678 registros**, o maior valor pós-interrupção observado na série; o pico geral continua sendo 2021, com 726.",
        "- Em 2024, Volta Redonda ficou em **1,30 vez a referência nacional**; isso é uma diferença de registros assistenciais, não uma prova de que o risco individual de câncer seja 30% maior.",
        "- O salto da taxa nacional entre 2017 e 2018 exige cautela: ele pode refletir expansão ou mudança de cobertura/registro do painel, e não apenas mudança epidemiológica.",
        "- A queda de 2020 e a elevação de 2021–2022 não devem ser lidas como mudança direta do risco de adoecer: 2020–2022 é período de interrupção assistencial oncológica.",
        "- Em 2024, os maiores grupos detalhados foram mama (C50), cólon (C18), colo do útero (C53) e próstata (C61). O colo do útero aparece com volume alto e merece investigação de rastreamento, confirmação diagnóstica e acesso ao tratamento.",
        "- A comparação com o restante do RJ deve ser feita por residência e com denominadores, mas a razão de registros ainda pode refletir diferenças de acesso, completude e encaminhamento.",
        "- A média nacional funciona como referência de escala; ela não corrige diferenças de cobertura do SUS, composição etária, rastreamento ou completude entre territórios.",
        "",
        "## Limitações e próximos dados",
        "",
        "- O painel não substitui registro populacional de câncer nem permite estimar casos únicos fora das regras e da cobertura do sistema.",
        "- RHC deve ser usado para perfil hospitalar, estadiamento e tratamento, não para incidência populacional.",
        "- Ainda faltam, para uma análise mais impactante, estágio, tempo até tratamento, município do diagnóstico/tratamento, cobertura por unidade e série do RHC para residentes de Volta Redonda.",
        "- Nenhuma associação causal com CSN, poluição ou ocupação é estimada nesta etapa.",
    ]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_oncology_diagnoses(root: Path) -> tuple[Path, Path, Path]:
    rates, metadata, series_inputs = _build_series(root)
    detail, detail_input = _build_detail(root)
    output = root / "data" / "processed" / "painel_oncologia_diagnoses.parquet"
    detail_output = root / "data" / "processed" / "painel_oncologia_diagnoses_detail_2024.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    rates.to_parquet(output, index=False)
    detail.to_parquet(detail_output, index=False)
    report = _write_report(root, rates, detail, metadata)
    manifest = root / "reports" / "quality" / "painel_oncologia_diagnoses_manifest.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "descriptive_registered_diagnoses_not_population_incidence",
        **metadata,
        "outputs": [
            {"path": str(output.relative_to(root)), "sha256": sha256_file(output), "rows": int(len(rates))},
            {"path": str(detail_output.relative_to(root)), "sha256": sha256_file(detail_output), "rows": int(len(detail))},
            {"path": str(report.relative_to(root)), "sha256": sha256_file(report)},
        ],
        "input_files": [
            {"path": str(path.relative_to(root)), "sha256": sha256_file(path)}
            for path in [*series_inputs, detail_input]
        ],
        "rules": {
            "territory": "municipality of residence; Volta Redonda=330630, rest of RJ excludes Volta Redonda, Brazil is the national total",
            "panel_category": "Neoplasias Malignas (Lei no 12.732/12)",
            "rate": "registered cases divided by resident population times 100,000; descriptive coverage-dependent measure",
            "small_cells": "counts below five are omitted from the public technical table",
        },
        "notes": [
            "Painel-Oncologia sources are SIA BPA-I/APAC, SIH and SISCAN.",
            "The panel output is not treated as population incidence.",
            "2020-2022 are marked as cancer care disruption years.",
            "No causal inference or ecological attribution to CSN is authorized.",
        ],
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output, manifest, report
