from __future__ import annotations

import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .provenance import sha256_file


SIVEP_OUTCOMES = ["srag", "covid19", "influenza"]
GEOGRAPHIES = ["rj_total", "volta_redonda", "rest_of_rj_excluding_vr"]
VR_CODE = "330630"
START_PERIOD = pd.Timestamp("2019-01-01")
DEFAULT_END_PERIOD = pd.Timestamp("2025-12-01")


def _sivep_geography(codes: pd.Series, vr_code: str = VR_CODE) -> pd.Series:
    normalized = (
        codes.astype("string")
        .fillna("")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )
    in_rj = normalized.str.fullmatch(r"33\d{4}").fillna(False)
    geography = pd.Series("outside_rj", index=normalized.index, dtype="string")
    geography.loc[in_rj & normalized.eq(vr_code)] = "volta_redonda"
    geography.loc[in_rj & normalized.ne(vr_code)] = "rest_of_rj_excluding_vr"
    return geography


def _input_paths(root: Path) -> list[Path]:
    paths = sorted((root / "data" / "interim").glob("sivep_*_harmonized.parquet"))
    if not paths:
        raise FileNotFoundError("no harmonized SIVEP Parquet was found")
    return paths


def _observed_end_period(paths: list[Path]) -> pd.Timestamp:
    latest: list[pd.Timestamp] = []
    for path in paths:
        onset = pd.to_datetime(
            pd.read_parquet(path, columns=["symptom_onset_date"])["symptom_onset_date"],
            errors="coerce",
        )
        maximum = onset.max()
        if pd.notna(maximum):
            latest.append(pd.Timestamp(maximum).to_period("M").to_timestamp())
    return max(latest) if latest else DEFAULT_END_PERIOD


def _period_status(year: int) -> str:
    if year == 2026:
        return "provisional_partial_2026"
    if year == 2025:
        return "provisional_2025"
    return "surveillance_versioned"


def _load_monthly_counts(root: Path) -> tuple[pd.DataFrame, dict[str, object], list[Path]]:
    frames: list[pd.DataFrame] = []
    source_stats: list[dict[str, object]] = []
    input_paths = _input_paths(root)
    end_period = _observed_end_period(input_paths)
    for path in input_paths:
        frame = pd.read_parquet(
            path,
            columns=[
                "municipality_code_datasus",
                "symptom_onset_date",
                "final_classification_raw",
                "outcome_raw",
            ],
        )
        geography = _sivep_geography(frame["municipality_code_datasus"])
        in_rj = geography.isin(["volta_redonda", "rest_of_rj_excluding_vr"])
        onset = pd.to_datetime(frame["symptom_onset_date"], errors="coerce")
        in_window = onset.ge(START_PERIOD) & onset.le(end_period + pd.offsets.MonthEnd(1))
        usable = in_rj & onset.notna() & in_window
        classification = (
            frame["final_classification_raw"]
            .astype("string")
            .fillna("")
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
        )
        outcome_status = (
            frame["outcome_raw"]
            .astype("string")
            .fillna("")
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
        )
        base = pd.DataFrame(
            {
                "period": onset.dt.to_period("M").dt.to_timestamp(),
                "geography": geography,
                "death_any": outcome_status.isin(["2", "3"]).astype(int),
                "classification": classification,
            }
        ).loc[usable]
        outcome_frames: list[pd.DataFrame] = []
        masks = {
            "srag": pd.Series(True, index=base.index),
            "covid19": base["classification"].eq("5"),
            "influenza": base["classification"].eq("1"),
        }
        for outcome_id, mask in masks.items():
            selected = base.loc[mask]
            if selected.empty:
                continue
            aggregate = (
                selected.groupby(["period", "geography"], as_index=False)
                .agg(notification_count=("death_any", "size"), death_any_count=("death_any", "sum"))
            )
            aggregate["outcome_id"] = outcome_id
            outcome_frames.append(aggregate)
        if outcome_frames:
            frames.append(pd.concat(outcome_frames, ignore_index=True))
        source_stats.append(
            {
                "path": str(path.relative_to(root)),
                "sha256": sha256_file(path),
                "rows": int(len(frame)),
                "rj_rows": int(in_rj.sum()),
                "missing_onset_rj_rows": int((in_rj & onset.isna()).sum()),
                "outside_window_rj_rows": int((in_rj & onset.notna() & ~in_window).sum()),
            }
        )
    if not frames:
        raise ValueError("no SIVEP monthly counts were produced")
    observed = pd.concat(frames, ignore_index=True)
    observed = (
        observed.groupby(["period", "geography", "outcome_id"], as_index=False)[
            ["notification_count", "death_any_count"]
        ]
        .sum()
    )
    rest = observed.loc[observed["geography"].isin(["volta_redonda", "rest_of_rj_excluding_vr"])].copy()
    rj_total = (
        rest.groupby(["period", "outcome_id"], as_index=False)[["notification_count", "death_any_count"]]
        .sum()
        .assign(geography="rj_total")
    )
    observed = pd.concat([observed, rj_total], ignore_index=True)
    months = pd.date_range(START_PERIOD, end_period, freq="MS")
    grid = pd.DataFrame(
        itertools.product(months, GEOGRAPHIES, SIVEP_OUTCOMES),
        columns=["period", "geography", "outcome_id"],
    )
    data = grid.merge(observed, on=["period", "geography", "outcome_id"], how="left")
    data["notification_count"] = data["notification_count"].fillna(0).astype(int)
    data["death_any_count"] = data["death_any_count"].fillna(0).astype(int)
    data["year"] = data["period"].dt.year.astype(int)
    data["month"] = data["period"].dt.month.astype(int)
    population_path = root / "data" / "processed" / "population_denominators.parquet"
    if not population_path.exists():
        raise FileNotFoundError(f"population denominator Parquet is missing: {population_path}")
    population = pd.read_parquet(population_path)
    population = population.loc[population["geography"].isin(GEOGRAPHIES), ["year", "geography", "population"]]
    data = data.merge(population, on=["year", "geography"], how="left", validate="many_to_one")
    monthly_population = data["population"] / 12
    data["notification_rate_per_100k"] = (
        data["notification_count"] / monthly_population * 100_000
    ).where(data["population"].notna())
    data["death_any_pct"] = (
        data["death_any_count"] / data["notification_count"] * 100
    ).where(data["notification_count"].gt(0))
    data["period_status"] = data["year"].map(_period_status)
    data = data.sort_values(["period", "outcome_id", "geography"]).reset_index(drop=True)
    metadata = {
        "start_period": START_PERIOD.strftime("%Y-%m"),
        "end_period": end_period.strftime("%Y-%m"),
        "rows": int(len(data)),
        "partial_years": [int(end_period.year)] if end_period.month < 12 else [],
        "provisional_years": [2025, 2026],
        "missing_denominator_years": sorted(
            int(year) for year in set(data["year"].unique()) - set(population["year"].unique())
        ),
        "source_stats": source_stats,
    }
    return data, metadata, _input_paths(root)


def _write_report(root: Path, data: pd.DataFrame, metadata: dict[str, object], input_paths: list[Path]) -> Path:
    report = root / "reports" / "technical" / "sivep_mensal.md"
    annual = (
        data.groupby(["year", "geography", "outcome_id"], as_index=False)[
            ["notification_count", "death_any_count"]
        ]
        .sum()
        .merge(
            data[["year", "geography", "population"]].drop_duplicates(),
            on=["year", "geography"],
            how="left",
        )
    )
    annual["rate"] = annual["notification_count"] / annual["population"] * 100_000
    rows = []
    selected = annual.loc[
        annual["geography"].isin(["volta_redonda", "rest_of_rj_excluding_vr"])
    ].sort_values(["year", "outcome_id", "geography"])
    for row in selected.itertuples(index=False):
        count = "<5" if row.notification_count < 5 else str(int(row.notification_count))
        rate = "—" if pd.isna(row.population) else f"{row.rate:.2f}"
        deaths = "<5" if row.death_any_count < 5 else str(int(row.death_any_count))
        rows.append(
            f"| {row.year} | {row.geography} | {row.outcome_id} | {count} | {rate} | {deaths} |"
        )
    lines = [
        "# Série mensal do SIVEP por início dos sintomas",
        "",
        f"Execução: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "As notificações são agregadas pelo mês de início dos sintomas (`DT_SIN_PRI`) "
        "e pelo município de residência. `srag` inclui todas as notificações elegíveis; "
        "Covid-19 e influenza permanecem como séries independentes. A taxa é de "
        "notificação, não incidência populacional.",
        "",
        f"- Janela mensal: **{metadata['start_period']} a {metadata['end_period']}**.",
        f"- Linhas do Parquet: **{metadata['rows']}**.",
        f"- Anos sem denominador: **{metadata['missing_denominator_years']}**.",
        f"- 2025 é provisório; 2026 é parcial até **{metadata['end_period']}** na versão adquirida. "
        "Eventos fora da janela e datas de início ausentes são registrados no manifesto.",
        "- Células menores que cinco são suprimidas nesta tabela.",
        "",
        "## Totais anuais de controle",
        "",
        "| ano | território | desfecho | notificações | notificações/100 mil | óbitos entre notificações |",
        "|---:|---|---|---:|---:|---:|",
        *rows,
        "",
        "A diferença entre arquivos anuais vivos, mudanças de cobertura, definição de caso e "
        "revisões impede interpretar a série como incidência sem auditoria específica. A "
        "análise temporal interrompida mensal do SIVEP permanece uma etapa posterior e não "
        "é estimada neste produto.",
        "",
        "## Proveniência",
        "",
        *[f"- `{path.relative_to(root)}` — SHA-256 `{sha256_file(path)}`" for path in input_paths],
    ]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_sivep_monthly(root: Path) -> tuple[Path, Path, Path]:
    data, metadata, input_paths = _load_monthly_counts(root)
    output = root / "data" / "processed" / "sivep_monthly_surveillance.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_parquet(output, index=False)
    report = _write_report(root, data, metadata, input_paths)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "monthly_sivep_surveillance_notification_rates_no_incidence",
        **metadata,
        "output_path": str(output.relative_to(root)),
        "output_sha256": sha256_file(output),
        "report_path": str(report.relative_to(root)),
        "input_files": [
            {"path": str(path.relative_to(root)), "sha256": sha256_file(path)}
            for path in input_paths
        ],
        "rules": {
            "date": "symptom onset date DT_SIN_PRI",
            "residence": "CO_MUN_RES; rest of RJ excludes DATASUS 330630",
            "srag": "all eligible SIVEP records",
            "covid19": "CLASSI_FIN=5",
            "influenza": "CLASSI_FIN=1",
        },
        "notes": [
            "Notification rates are not incidence rates.",
            "2025 is provisional; 2026 is partial through the observed end period and both versions are subject to revision.",
            "No causal or interrupted time-series inference is produced here.",
        ],
    }
    manifest_path = root / "reports" / "quality" / "sivep_monthly_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output, manifest_path, report
