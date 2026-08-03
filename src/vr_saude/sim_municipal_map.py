from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import load_config
from .mortality import period_status
from .outcomes import OUTCOME_SECTIONS, _matches_cid
from .provenance import sha256_file
from .rates import RATE_MULTIPLIER, poisson_count_interval


def _definitions(root: Path) -> list[dict[str, object]]:
    config = load_config("outcomes.yml", root)
    return [
        item
        for section in OUTCOME_SECTIONS
        for item in config.get(section, [])
        if "SIM" in item.get("source", []) and item.get("code_ranges")
    ]


def _population(root: Path, year: int) -> pd.DataFrame:
    path = root / "data" / "processed" / "population_rj_municipality.parquet"
    if not path.exists():
        raise FileNotFoundError(f"RJ municipality population is missing: {path}")
    population = pd.read_parquet(path)
    population = population.loc[population["year"].eq(year)].copy()
    population["municipality_code_ibge"] = population["municipality_code_ibge"].astype(str)
    if len(population) != 92 or population["municipality_code_ibge"].nunique() != 92:
        raise ValueError(f"population denominator for {year} must contain exactly 92 RJ municipalities")
    population["municipality_code_datasus"] = population["municipality_code_ibge"].str[:6]
    return population[["municipality_code_ibge", "municipality_code_datasus", "municipality_name", "population"]]


def _counts(root: Path, definitions: list[dict[str, object]], year: int) -> tuple[pd.DataFrame, Path, Path]:
    harmonized = root / "data" / "interim" / f"sim_{year}_harmonized.parquet"
    if not harmonized.exists():
        raise FileNotFoundError(f"harmonized SIM {year} file is missing: {harmonized}")
    frame = pd.read_parquet(harmonized, columns=["source_file", "municipality_code_datasus", "residence_code_valid", "underlying_cause"])
    residence = frame["municipality_code_datasus"].fillna("").astype(str).str.strip()
    rj = frame["residence_code_valid"].fillna(False) & residence.str.fullmatch(r"33\d{4}")
    codes = frame["underlying_cause"].fillna("").astype(str).str.upper().str.replace(".", "", regex=False).str.strip()
    rows: list[pd.DataFrame] = []
    for definition in definitions:
        mask = rj & _matches_cid(codes, list(definition["code_ranges"]))
        if mask.any():
            rows.append(pd.DataFrame({
                "municipality_code_datasus": residence.loc[mask],
                "outcome_id": str(definition["id"]),
                "count": 1,
            }))
    if not rows:
        raise ValueError(f"SIM {year} has no classified RJ resident deaths")
    counts = pd.concat(rows, ignore_index=True)
    counts = counts.groupby(["municipality_code_datasus", "outcome_id"], as_index=False)["count"].sum()
    source_paths = frame["source_file"].dropna().astype(str).unique().tolist()
    if len(source_paths) != 1:
        raise ValueError(f"SIM {year} must reference exactly one raw source file")
    raw = root / source_paths[0]
    if not raw.exists():
        raise FileNotFoundError(f"SIM {year} raw provenance file is missing: {raw}")
    return counts, raw, harmonized


def build_sim_municipal_map(root: Path, year: int = 2022) -> tuple[Path, Path, Path]:
    definitions = _definitions(root)
    population = _population(root, year)
    counts, raw, harmonized = _counts(root, definitions, year)
    outcomes = pd.DataFrame({"outcome_id": [str(item["id"]) for item in definitions]})
    municipalities = population[["municipality_code_ibge", "municipality_code_datasus", "municipality_name", "population"]]
    grid = municipalities.merge(outcomes, how="cross")
    rates = grid.merge(counts, how="left", on=["municipality_code_datasus", "outcome_id"])
    rates["count"] = rates["count"].fillna(0).astype(int)
    rates["year"] = year
    rates["rate_per_100k"] = rates["count"] / rates["population"] * RATE_MULTIPLIER
    intervals = [poisson_count_interval(int(value)) for value in rates["count"]]
    rates["rate_ci_lower_per_100k"] = [low / pop * RATE_MULTIPLIER for (low, _), pop in zip(intervals, rates["population"])]
    rates["rate_ci_upper_per_100k"] = [high / pop * RATE_MULTIPLIER for (_, high), pop in zip(intervals, rates["population"])]
    rates["period_status"] = [period_status(root, year, outcome_id) for outcome_id in rates["outcome_id"]]
    rates = rates.sort_values(["outcome_id", "municipality_code_ibge"]).reset_index(drop=True)

    output = root / "data" / "processed" / f"sim_municipal_map_rates_{year}.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    rates.to_parquet(output, index=False)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": f"validated_sim_{year}_municipal_residence_rates_crude",
        "year": year,
        "municipalities": int(rates["municipality_code_ibge"].nunique()),
        "outcome_ids": sorted(rates["outcome_id"].unique().tolist()),
        "rows": int(len(rates)),
        "suppressed_cells_lt_5": int((rates["count"] < 5).sum()),
        "output_path": str(output.relative_to(root)),
        "output_sha256": sha256_file(output),
        "input_files": [
            {"path": str(raw.relative_to(root)), "sha256": sha256_file(raw)},
            {"path": str(harmonized.relative_to(root)), "sha256": sha256_file(harmonized)},
            {
                "path": "data/processed/population_rj_municipality.parquet",
                "sha256": sha256_file(root / "data" / "processed" / "population_rj_municipality.parquet"),
            },
        ],
        "rules": {
            "residence": "CODMUNRES DATASUS six-digit code mapped to IBGE seven-digit municipality code",
            "rate": f"SIM underlying-cause deaths of residents divided by the validated {year} resident population times 100,000",
            "interval": "exact Poisson 95% interval",
            "suppression": "count < 5 is withheld before portal publication",
        },
        "notes": [
            f"This is a {year} municipal snapshot; continuity depends on separately validated years.",
            "SIM cancer mortality is not incidence.",
            "No causal inference or attribution to CSN is produced.",
        ],
    }
    manifest_path = root / "reports" / "quality" / f"sim_municipal_map_{year}_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = root / "reports" / "technical" / f"mapa_municipal_sim_{year}.md"
    report_path.write_text(
        "\n".join(
            [
                f"# Camada municipal SIM {year}",
                "",
                f"Execução: {manifest['generated_at']}",
                "",
                f"A camada usa município de residência (`CODMUNRES`) e população residente validada para {year}. "
                "É uma fotografia municipal de mortalidade; não representa incidência de câncer, "
                "não interpola anos e não autoriza atribuição causal.",
                "",
                f"- Municípios: **{manifest['municipalities']}**.",
                f"- Desfechos: **{len(manifest['outcome_ids'])}**.",
                f"- Células suprimidas antes da publicação: **{manifest['suppressed_cells_lt_5']}**.",
                "- SIH permanece sem valores municipais até a validação de RD-AIH por residência.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return output, manifest_path, report_path
