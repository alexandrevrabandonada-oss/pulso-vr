from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import load_config
from .provenance import sha256_file
from .rates import RATE_MULTIPLIER, poisson_count_interval

OUTCOMES = ("alzheimer", "dementias_all")


def _parse_brazil_month(path: Path) -> dict[str, int]:
    text = html.unescape(path.read_bytes().decode("latin1"))
    counts = {"alzheimer": 0, "dementias_all": 0}
    for raw_line in text.splitlines():
        match = re.match(r'^"([^\"]+)";([0-9.,-]+)', raw_line.strip())
        if not match:
            continue
        label = re.sub(r"^\.+\s*", "", match.group(1)).strip().lower()
        raw_value = match.group(2)
        value = 0 if raw_value == "-" else int(raw_value.replace(".", "").replace(",", ""))
        if label == "doença de alzheimer":
            counts["alzheimer"] += value
        elif label == "demência":
            counts["dementias_all"] += value
    if counts["alzheimer"] == 0 or counts["dementias_all"] == 0:
        raise ValueError(f"Brazil SIH month has no validated Alzheimer/dementia labels: {path}")
    return counts


def build_sih_neurological_rates(root: Path, year: int = 2022) -> tuple[Path, Path, Path]:
    municipal_path = root / "data" / "processed" / f"sih_municipal_map_rates_{year}.parquet"
    if not municipal_path.exists():
        raise FileNotFoundError(f"SIH neurological municipal map is missing: {municipal_path}")
    municipal = pd.read_parquet(municipal_path)
    municipal = municipal.loc[municipal["outcome_id"].isin(OUTCOMES)].copy()
    if municipal["municipality_code_ibge"].nunique() != 92:
        raise ValueError("SIH neurological municipal map must contain all 92 municipalities")

    population = pd.read_parquet(root / "data" / "processed" / "population_denominators.parquet")
    population = population.loc[population["year"].eq(year)].set_index("geography")["population"]
    territory = load_config("territories.yml", root)
    vr_code = str(territory["volta_redonda"]["ibge_code_7"])

    aggregate_rows: list[dict[str, object]] = []
    for outcome_id, group in municipal.groupby("outcome_id", sort=True):
        rj_count = int(group["count"].sum())
        vr_count = int(group.loc[group["municipality_code_ibge"].eq(vr_code), "count"].sum())
        brazil_counts = {outcome: 0 for outcome in OUTCOMES}
        for path in sorted((root / "data" / "raw").glob(f"sih_tabnet_nrbr_morbidity_brazil_total_{year}_*.html")):
            month_counts = _parse_brazil_month(path)
            for outcome, value in month_counts.items():
                brazil_counts[outcome] += value
        counts = {
            "rj_total": rj_count,
            "rest_of_rj_excluding_vr": rj_count - vr_count,
            "brazil_total": brazil_counts[outcome_id],
            "volta_redonda": vr_count,
        }
        labels = {
            "alzheimer": "Doença de Alzheimer",
            "dementias_all": "Doença de Alzheimer e outras demências",
        }
        for geography, count in counts.items():
            denominator = int(population[geography])
            low, high = poisson_count_interval(count)
            aggregate_rows.append({
                "year": year,
                "outcome_id": outcome_id,
                "outcome_label": labels[outcome_id],
                "geography": geography,
                "count": count,
                "denominator": denominator,
                "rate_per_100k": count / denominator * RATE_MULTIPLIER,
                "rate_ci_lower_per_100k": low / denominator * RATE_MULTIPLIER,
                "rate_ci_upper_per_100k": high / denominator * RATE_MULTIPLIER,
                "period_status": "provisional" if year >= 2025 else "source_year_observed",
            })

    municipal_rows = municipal.rename(columns={"population": "denominator"})[
        ["year", "outcome_id", "municipality_code_ibge", "count", "denominator", "rate_per_100k", "rate_ci_lower_per_100k", "rate_ci_upper_per_100k", "period_status"]
    ].rename(columns={"municipality_code_ibge": "geography"})
    municipal_rows["outcome_label"] = municipal_rows["outcome_id"].map({
        "alzheimer": "Doença de Alzheimer",
        "dementias_all": "Doença de Alzheimer e outras demências",
    })
    output_frame = pd.concat([municipal_rows, pd.DataFrame(aggregate_rows)], ignore_index=True)
    output = root / "data" / "processed" / "sih_neurological_rates_annual.parquet"
    output_frame.to_parquet(output, index=False)
    input_files = [{"path": str(path.relative_to(root)), "sha256": sha256_file(path)} for path in sorted((root / "data" / "raw").glob(f"sih_tabnet_nrbr_morbidity_brazil_total_{year}_*.html"))]
    input_files.append({"path": str(municipal_path.relative_to(root)), "sha256": sha256_file(municipal_path)})
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "validated_sih_neurological_residence_rates",
        "year": year,
        "outcome_ids": list(OUTCOMES),
        "municipalities": 92,
        "geographies": ["volta_redonda", "rest_of_rj_excluding_vr", "rj_total", "brazil_total"],
        "rows": len(output_frame),
        "output_path": str(output.relative_to(root)),
        "output_sha256": sha256_file(output),
        "input_files": input_files,
        "rules": {
            "residence": "SIH municipality of residence",
            "measure": "AIH/hospitalization event, not unique person",
            "diagnostic_groups": {"alzheimer": "146 Doença de Alzheimer", "dementias_all": "132 Demência + 146 Doença de Alzheimer"},
        },
    }
    manifest_path = root / "reports" / "quality" / "sih_neurological_rates_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = root / "reports" / "technical" / "sih_alzheimer_demencias.md"
    report_path.write_text(
        f"# Internações SIH por Alzheimer e demências — {year}\n\n"
        "A camada usa município de residência e trata cada AIH como evento de internação. "
        "O Brasil foi agregado a partir dos 12 arquivos mensais NRBR com os grupos oficiais "
        "132 (Demência) e 146 (Doença de Alzheimer).\n",
        encoding="utf-8",
    )
    return output, manifest_path, report_path
