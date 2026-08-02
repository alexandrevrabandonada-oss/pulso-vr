from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .provenance import sha256_file


SURVEILLANCE_OUTCOMES = ["srag", "covid19", "influenza"]
DEATH_STATUSES = {"óbito por SRAG", "óbito por outra causa"}


def notification_rate_per_100k(count: int, population: int) -> float:
    if count < 0 or population <= 0:
        raise ValueError("count must be non-negative and population must be positive")
    return count / population * 100_000


def _load_inputs(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, Path, Path]:
    counts_path = root / "data" / "processed" / "outcome_counts_sim_sivep.parquet"
    population_path = root / "data" / "processed" / "population_denominators.parquet"
    if not counts_path.exists():
        raise FileNotFoundError(f"outcome counts Parquet is missing: {counts_path}")
    if not population_path.exists():
        raise FileNotFoundError(f"population denominator Parquet is missing: {population_path}")
    counts = pd.read_parquet(counts_path)
    population = pd.read_parquet(population_path)
    counts = counts.loc[
        (counts["source"] == "SIVEP-SRAG") & counts["outcome_id"].isin(SURVEILLANCE_OUTCOMES)
    ].copy()
    population = population.loc[population["year"].isin(counts["source_year"].unique())].copy()
    return counts, population, counts_path, population_path


def _write_report(root: Path, summary: pd.DataFrame, metadata: dict[str, object]) -> Path:
    report = root / "reports" / "technical" / "pandemia_sivep.md"
    rows = []
    for row in summary.sort_values(["year", "outcome_id", "geography"]).itertuples(index=False):
        count = "<5" if row.notification_count < 5 else str(int(row.notification_count))
        deaths = "<5" if row.death_any_count < 5 else str(int(row.death_any_count))
        rate = f"{row.notification_rate_per_100k:.2f}" if pd.notna(row.population) else "—"
        fatality = f"{row.death_any_pct:.2f}" if pd.notna(row.death_any_pct) else "—"
        rows.append(
            f"| {row.year} | {row.geography} | {row.outcome_id} | {count} | {rate} | {deaths} | {fatality} |"
        )
    lines = [
        "# Síntese pandêmica do SIVEP",
        "",
        f"Execução: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "O SIVEP é uma base de vigilância de SRAG. As taxas abaixo são taxas de "
        "notificação por 100 mil residentes, não incidência, e dependem de cobertura, "
        "definição de caso, completude e atualização do sistema.",
        "",
        f"- Linhas agregadas: **{len(summary)}**.",
        f"- Anos disponíveis: **{metadata['available_years']}**.",
        f"- Anos sem denominador: **{metadata['missing_denominator_years']}**.",
        "- 2020 é marcado como período pandêmico; março de 2020 é a ruptura mensal definida no protocolo.",
        "- Células menores que cinco são exibidas como `<5`.",
        "",
        "## Notificações e óbitos entre notificações",
        "",
        "| ano | território | desfecho | notificações | notificações/100 mil | óbitos | % óbitos/notificações |",
        "|---:|---|---|---:|---:|---:|---:|",
        *rows,
        "",
        "A proporção de óbitos é descritiva entre notificações com os códigos de evolução "
        "observados; não é letalidade populacional. Não há modelo de série temporal "
        "interrompida com apenas estes dois anos.",
        "",
        "## Limitações",
        "",
        "- 2019 e 2020 são arquivos SIVEP versionados, sujeitos a revisão e mudanças de cobertura.",
        "- O comparador territorial usa residência e exclui Volta Redonda do restante do RJ.",
        "- Não há ajuste por idade, sexo, vacinação, circulação viral, sazonalidade ou acesso.",
        "- Nenhuma associação com poluição ou CSN é estimada nesta etapa.",
    ]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_sivep_surveillance_summary(root: Path) -> tuple[Path, Path, Path]:
    counts, population, counts_path, population_path = _load_inputs(root)
    if counts.empty:
        raise ValueError("no SIVEP surveillance outcomes available")
    keys = ["source_year", "geography", "outcome_id", "outcome_label", "unit"]
    summary = counts.groupby(keys, as_index=False)["count"].sum().rename(columns={"count": "notification_count"})
    status = (
        counts.groupby(keys + ["outcome_status"], as_index=False)["count"]
        .sum()
        .pivot_table(index=keys, columns="outcome_status", values="count", fill_value=0, aggfunc="sum")
        .reset_index()
    )
    status.columns.name = None
    status = status.rename(
        columns={
            "óbito por SRAG": "death_srag_count",
            "óbito por outra causa": "death_other_count",
        }
    )
    for column in ["death_srag_count", "death_other_count"]:
        if column not in status.columns:
            status[column] = 0
    summary = summary.merge(status, on=keys, how="left", validate="one_to_one")
    summary["death_srag_count"] = summary["death_srag_count"].fillna(0).astype(int)
    summary["death_other_count"] = summary["death_other_count"].fillna(0).astype(int)
    summary["death_any_count"] = summary["death_srag_count"] + summary["death_other_count"]
    summary = summary.merge(
        population[["year", "geography", "population", "source_status"]].rename(columns={"year": "source_year"}),
        on=["source_year", "geography"],
        how="left",
        validate="many_to_one",
    )
    summary["notification_rate_per_100k"] = summary.apply(
        lambda row: notification_rate_per_100k(int(row.notification_count), int(row.population))
        if pd.notna(row.population)
        else float("nan"),
        axis=1,
    )
    summary["death_any_pct"] = summary.apply(
        lambda row: int(row.death_any_count) / int(row.notification_count) * 100
        if row.notification_count
        else float("nan"),
        axis=1,
    )
    summary = summary.rename(columns={"source_year": "year", "source_status": "population_source_status"})
    summary = summary.sort_values(["year", "outcome_id", "geography"]).reset_index(drop=True)
    output = root / "data" / "processed" / "sivep_surveillance_summary.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_parquet(output, index=False)
    missing_denominator_years = sorted(
        set(summary["year"].unique()) - set(population["year"].unique())
    )
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "surveillance_notification_rates_no_incidence_estimate",
        "rows": int(len(summary)),
        "available_years": sorted(summary["year"].unique().tolist()),
        "missing_denominator_years": missing_denominator_years,
        "output_path": str(output.relative_to(root)),
        "output_sha256": sha256_file(output),
        "input_files": [
            {"path": str(counts_path.relative_to(root)), "sha256": sha256_file(counts_path)},
            {"path": str(population_path.relative_to(root)), "sha256": sha256_file(population_path)},
        ],
        "rules": {
            "outcomes": SURVEILLANCE_OUTCOMES,
            "death_statuses": sorted(DEATH_STATUSES),
            "territory": "residence; rj_total, Volta Redonda and rest of RJ excluding VR",
        },
        "notes": [
            "Notification rates are not incidence rates and should not be interpreted as risk of infection.",
            "SIVEP coverage and case definitions change over time; 2019 and 2020 are not automatically comparable.",
            "Small counts are suppressed in the technical report.",
            "No causal or interrupted time-series inference is produced.",
        ],
    }
    manifest_path = root / "reports" / "quality" / "sivep_surveillance_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = _write_report(
        root,
        summary,
        {"available_years": sorted(summary["year"].unique().tolist()), "missing_denominator_years": missing_denominator_years},
    )
    return output, manifest_path, report_path
