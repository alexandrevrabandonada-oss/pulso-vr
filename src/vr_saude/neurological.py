from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import duckdb

from .config import load_config
from .outcomes import _geography, _matches_cid, _normalize_code
from .provenance import sha256_file
from .rates import RATE_MULTIPLIER, poisson_count_interval

OUTCOMES = ("alzheimer", "dementias_all")
AGGREGATE_GEOGRAPHIES = ("brazil_total", "rj_total", "volta_redonda", "rest_of_rj_excluding_vr")


def _definitions(root: Path) -> dict[str, dict[str, object]]:
    config = load_config("outcomes.yml", root)
    return {
        str(item["id"]): item
        for item in config.get("neurological", [])
        if "SIM" in item.get("source", []) and str(item["id"]) in OUTCOMES
    }


def _year(path: Path) -> int:
    match = re.search(r"sim_(\d{4})_harmonized", path.name)
    if not match:
        raise ValueError(f"cannot infer SIM year from {path.name}")
    return int(match.group(1))


def _counts_for_file(root: Path, path: Path, definitions: dict[str, dict[str, object]]) -> pd.DataFrame:
    territory_config = load_config("territories.yml", root)
    vr_code = str(territory_config["volta_redonda"]["datasus_code_6_expected"])
    rows: list[dict[str, object]] = []
    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(columns=["municipality_code_datasus", "underlying_cause"], batch_size=250_000):
        chunk = batch.to_pandas()
        codes = _normalize_code(chunk["underlying_cause"])
        geography = _geography(chunk["municipality_code_datasus"], vr_code)
        eligible = geography.ne("outside_brazil")
        for outcome_id, definition in definitions.items():
            mask = eligible & _matches_cid(codes, list(definition["code_ranges"]))
            if not mask.any():
                continue
            values = geography.loc[mask].value_counts()
            rows.extend({"geography": str(geo), "outcome_id": outcome_id, "count": int(count)} for geo, count in values.items())
    if not rows:
        return pd.DataFrame(columns=["geography", "outcome_id", "count"])
    frame = pd.DataFrame(rows).groupby(["geography", "outcome_id"], as_index=False)["count"].sum()
    return frame


def build_neurological_rates(root: Path) -> tuple[Path, Path, Path]:
    definitions = _definitions(root)
    paths = sorted((root / "data" / "interim").glob("sim_*_harmonized.parquet"))
    if not paths:
        raise FileNotFoundError("no harmonized SIM files available")
    population_path = root / "data" / "processed" / "population_denominators.parquet"
    if not population_path.exists():
        raise FileNotFoundError(f"population denominators are missing: {population_path}")
    population = pd.read_parquet(population_path)
    population["year"] = population["year"].astype(int)
    population["population"] = population["population"].astype(int)
    municipal_population_path = root / "data" / "processed" / "population_rj_municipality.parquet"
    if not municipal_population_path.exists():
        raise FileNotFoundError(f"municipal population denominators are missing: {municipal_population_path}")
    municipal_population = pd.read_parquet(municipal_population_path)
    municipal_population["year"] = municipal_population["year"].astype(int)
    municipal_population["municipality_code_ibge"] = municipal_population["municipality_code_ibge"].astype(str)
    municipal_population["datasus_code"] = municipal_population["municipality_code_ibge"].str[:6]
    municipal_population["municipality_code_ibge"] = municipal_population["municipality_code_ibge"].astype(object)
    municipal_population["datasus_code"] = municipal_population["datasus_code"].astype(object)
    municipal_population = municipal_population.drop_duplicates(["year", "datasus_code"])
    municipality_codes = sorted(municipal_population["municipality_code_ibge"].unique().tolist())
    input_files = [
        {"path": str(path.relative_to(root)), "sha256": sha256_file(path), "year": _year(path)}
        for path in paths if _year(path) <= 2025
    ]
    glob_path = str((root / "data" / "interim" / "sim_*_harmonized.parquet")).replace("\\", "/")
    territory_config = load_config("territories.yml", root)
    vr_ibge_code = str(territory_config["volta_redonda"]["ibge_code_7"])
    connection = duckdb.connect(database=":memory:")
    connection.register("municipal_population", municipal_population[["year", "datasus_code", "municipality_code_ibge"]])
    query = f"""
        WITH base AS (
            SELECT
                CAST(source_year AS INTEGER) AS year,
                trim(CAST(municipality_code_datasus AS VARCHAR)) AS datasus_code,
                upper(replace(coalesce(CAST(underlying_cause AS VARCHAR), ''), '.', '')) AS cause
            FROM read_parquet('{glob_path}')
            WHERE CAST(source_year AS INTEGER) BETWEEN 2010 AND 2025
        ), mapped AS (
            SELECT
                b.year,
                COALESCE(m.municipality_code_ibge,
                    CASE WHEN regexp_matches(b.datasus_code, '^[0-9]{{6}}$') THEN 'rest_of_brazil_excluding_rj' ELSE NULL END
                ) AS geography,
                b.cause
            FROM base b
            LEFT JOIN municipal_population m
                ON m.year = b.year AND m.datasus_code = b.datasus_code
        ), classified AS (
            SELECT
                year,
                geography,
                SUM(CASE WHEN starts_with(cause, 'G30') OR cause IN ('F000', 'F001', 'F002') THEN 1 ELSE 0 END)::INTEGER AS alzheimer,
                SUM(CASE WHEN starts_with(cause, 'G30') OR starts_with(cause, 'F00') OR starts_with(cause, 'F01') OR starts_with(cause, 'F02') OR starts_with(cause, 'F03') THEN 1 ELSE 0 END)::INTEGER AS dementias_all
            FROM mapped
            WHERE geography IS NOT NULL
            GROUP BY year, geography
        ), totals AS (
            SELECT year, 'rj_total' AS geography, SUM(alzheimer)::INTEGER AS alzheimer, SUM(dementias_all)::INTEGER AS dementias_all
            FROM classified WHERE regexp_matches(geography, '^33[0-9]{{5}}$') GROUP BY year
            UNION ALL
            SELECT year, 'brazil_total' AS geography, SUM(alzheimer)::INTEGER AS alzheimer, SUM(dementias_all)::INTEGER AS dementias_all
            FROM classified GROUP BY year
            UNION ALL
            SELECT r.year, 'rest_of_rj_excluding_vr' AS geography,
                   (r.alzheimer - COALESCE(v.alzheimer, 0))::INTEGER AS alzheimer,
                   (r.dementias_all - COALESCE(v.dementias_all, 0))::INTEGER AS dementias_all
            FROM (
                SELECT year, SUM(alzheimer)::INTEGER AS alzheimer, SUM(dementias_all)::INTEGER AS dementias_all
                FROM classified WHERE regexp_matches(geography, '^33[0-9]{{5}}$') GROUP BY year
            ) r
            LEFT JOIN classified v ON v.year = r.year AND v.geography = '{vr_ibge_code}'
        )
        SELECT * FROM classified
        UNION ALL
        SELECT * FROM totals
    """
    wide = connection.execute(query).fetch_df()
    connection.close()
    observed_years = sorted(wide["year"].unique().tolist())
    geographies = municipality_codes + list(AGGREGATE_GEOGRAPHIES)
    grid = pd.MultiIndex.from_product(
        [observed_years, geographies],
        names=["year", "geography"],
    ).to_frame(index=False)
    wide = grid.merge(wide, on=["year", "geography"], how="left")
    wide[["alzheimer", "dementias_all"]] = wide[["alzheimer", "dementias_all"]].fillna(0).astype(int)
    counts = wide.melt(id_vars=["year", "geography"], var_name="outcome_id", value_name="count")
    counts["outcome_label"] = counts["outcome_id"].map({
        "alzheimer": "Doença de Alzheimer",
        "dementias_all": "Doença de Alzheimer e outras demências",
    })
    municipal_population_for_merge = municipal_population[["year", "municipality_code_ibge", "population", "source_status"]].rename(
        columns={"municipality_code_ibge": "geography"}
    )
    aggregate_population_for_merge = population[["year", "geography", "population", "source_status"]]
    denominators = pd.concat([municipal_population_for_merge, aggregate_population_for_merge], ignore_index=True)
    counts = counts.merge(
        denominators,
        on=["year", "geography"],
        how="left",
        validate="many_to_one",
    )
    counts = counts.loc[counts["population"].notna()].copy()
    counts["population"] = counts["population"].astype(int)
    intervals = [poisson_count_interval(int(value)) for value in counts["count"]]
    counts["rate_per_100k"] = counts["count"] / counts["population"] * RATE_MULTIPLIER
    counts["rate_ci_lower_per_100k"] = [low / pop * RATE_MULTIPLIER for (low, _), pop in zip(intervals, counts["population"])]
    counts["rate_ci_upper_per_100k"] = [high / pop * RATE_MULTIPLIER for (_, high), pop in zip(intervals, counts["population"])]
    counts["period_status"] = counts["year"].map(lambda year: "neurological_provisional" if year >= 2025 else "source_year_observed")
    counts = counts.rename(columns={"source_status": "population_source_status"})
    counts = counts.sort_values(["year", "outcome_id", "geography"]).reset_index(drop=True)
    output = root / "data" / "processed" / "sim_neurological_rates_annual.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    counts.to_parquet(output, index=False)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "validated_sim_neurological_crude_residence_rates",
        "years": sorted(counts["year"].unique().tolist()),
        "outcome_ids": list(OUTCOMES),
        "geographies": geographies,
        "rows": int(len(counts)),
        "output_path": str(output.relative_to(root)),
        "output_sha256": sha256_file(output),
        "input_files": input_files,
        "population_input": {"path": str(population_path.relative_to(root)), "sha256": sha256_file(population_path)},
        "rules": {
            "residence": "SIM municipality of residence",
            "rate": "underlying-cause deaths / resident population × 100,000",
            "comparison": "municipality-specific rest of RJ must be calculated from aggregate numerator and denominator",
            "suppression": "count < 5 withheld before public publication",
        },
    }
    manifest_path = root / "reports" / "quality" / "sim_neurological_rates_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = root / "reports" / "technical" / "mortalidade_alzheimer_demencias.md"
    report_path.write_text(
        "# Mortalidade por Alzheimer e demências\n\n"
        "Série anual de óbitos de residentes classificados pela causa básica no SIM. "
        "A taxa descreve mortalidade registrada e não mede prevalência ou incidência. "
        "2025 é mantido como provisório quando presente.\n",
        encoding="utf-8",
    )
    return output, manifest_path, report_path
