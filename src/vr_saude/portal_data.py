from __future__ import annotations

import csv
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .config import load_config
from .download import download_public_file
from .provenance import sha256_file
from .rates import RATE_MULTIPLIER
from .standardization import direct_standardized_rate


SMALL_CELL_THRESHOLD = 5
GEOGRAPHY_URL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/estados/33"
    "?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=municipio"
)
GEOGRAPHY_RAW_FILENAME = "ibge_malha_municipal_rj_minima.geojson"

GEOGRAPHY_LABELS = {
    "volta_redonda": "Volta Redonda",
    "rest_of_rj_excluding_vr": "RJ sem Volta Redonda",
    "rj_total": "Rio de Janeiro (total)",
    "brazil_total": "Brasil",
}

SOURCE_DEFINITIONS = {
    "SIH": {
        "measure": "hospitalization",
        "measureLabel": "Internações hospitalares (AIHs)",
        "unit": "internações/AIHs de residentes",
        "sourceLabel": "SIH/SUS — DATASUS",
        "definition": (
            "Eventos de internação registrados em Autorizações de Internação Hospitalar "
            "por município de residência. Não representam pessoas únicas nem casos novos."
        ),
    },
    "SIM": {
        "measure": "mortality",
        "measureLabel": "Mortalidade",
        "unit": "óbitos de residentes pela causa básica",
        "sourceLabel": "SIM — Ministério da Saúde",
        "definition": (
            "Óbitos de residentes classificados pela causa básica no Sistema de Informação "
            "sobre Mortalidade. Esses óbitos não representam incidência, prevalência ou todos os casos existentes da doença."
        ),
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def suppress_public_observation(observation: dict[str, Any]) -> dict[str, Any]:
    count = observation.get("count")
    if count is not None and int(count) < SMALL_CELL_THRESHOLD:
        for field in ("value", "count", "ciLow", "ciHigh"):
            observation[field] = None
        observation["suppressed"] = True
        observation["suppressionReason"] = "small_cell_lt_5"
        observation["suppressionStatus"] = "suppressed"
    else:
        observation["suppressed"] = False
        observation["suppressionReason"] = None
        observation["suppressionStatus"] = "published" if observation.get("value") is not None else "unavailable"
    return observation


def _data_status(source: str, year: int, period_status: str) -> str:
    if "provisional" in period_status or (source == "SIH" and year >= 2025):
        return "provisional"
    return "source_observed"


def _finite_or_none(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _series_observations(frame: pd.DataFrame, source: str) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for row in frame.itertuples(index=False):
        period_status = str(row.period_status)
        outcome_id = str(row.outcome_id)
        observation = {
            "source": source,
            "outcomeId": outcome_id,
            "geographyId": str(row.geography),
            "period": str(int(row.year)),
            "metricKind": "crude_rate_per_100k",
            "value": _finite_or_none(row.rate_per_100k),
            "count": int(row.count),
            "denominator": int(row.denominator if source == "SIH" else row.population),
            "ciLow": _finite_or_none(row.rate_ci_lower_per_100k),
            "ciHigh": _finite_or_none(row.rate_ci_upper_per_100k),
            "dataStatus": _data_status(source, int(row.year), period_status),
            "periodStatus": period_status,
            "manifestRef": (
                "reports/quality/sih_neurological_rates_manifest.json"
                if source == "SIH" and outcome_id in {"alzheimer", "dementias_all"}
                else "reports/quality/respiratory_rates_manifest.json" if source == "SIH"
                else "reports/quality/sim_neurological_rates_manifest.json"
                if source == "SIM" and outcome_id in {"alzheimer", "dementias_all"}
                else "reports/quality/sim_mortality_rates_manifest.json"
            ),
            "geographyBasis": "residence",
        }
        observations.append(suppress_public_observation(observation))
    return observations


def _indicator_id(source: str, outcome_id: str) -> str:
    return f"{source.lower()}-{outcome_id.replace('_', '-')}"


def _theme(outcome_id: str, outcome_config: dict[str, set[str]]) -> str:
    for theme in ("respiratory", "cardiovascular", "cardiorespiratory", "cancer", "neurological"):
        if outcome_id in outcome_config[theme]:
            return theme
    raise ValueError(f"outcome is not assigned to a portal theme: {outcome_id}")


def _configured_outcomes(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, set[str]]]:
    config = load_config("outcomes.yml", root)
    by_id: dict[str, dict[str, Any]] = {}
    sections = {"respiratory": set(), "cardiovascular": set(), "cardiorespiratory": set(), "cancer": set(), "neurological": set()}
    for section in sections:
        for item in config.get(section, []):
            by_id[item["id"]] = item
            sections[section].add(item["id"])
    return by_id, sections


def _build_catalog_and_series(root: Path) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    configured, sections = _configured_outcomes(root)
    sources: list[tuple[str, Path | pd.DataFrame]] = [
        ("SIH", root / "data" / "processed" / "respiratory_rates_annual.parquet"),
    ]
    sih_neurological = root / "data" / "processed" / "sih_neurological_rates_annual.parquet"
    if sih_neurological.exists():
        sources.append(("SIH", sih_neurological))
    sim_frames = [
        pd.read_parquet(path) for path in (
            root / "data" / "processed" / "sim_mortality_rates_sample.parquet",
            root / "data" / "processed" / "sim_neurological_rates_annual.parquet",
        ) if path.exists()
    ]
    if sim_frames:
        sources.append(("SIM", pd.concat(sim_frames, ignore_index=True).drop_duplicates(["year", "geography", "outcome_id"], keep="last")))
    catalog: list[dict[str, Any]] = []
    series: dict[str, list[dict[str, Any]]] = {}
    for source, source_data in sources:
        if isinstance(source_data, Path):
            if not source_data.exists():
                continue
            frame = pd.read_parquet(source_data)
        else:
            frame = source_data
        for outcome_id, outcome_frame in frame.groupby("outcome_id", sort=True):
            source_definition = SOURCE_DEFINITIONS[source]
            indicator_id = _indicator_id(source, str(outcome_id))
            latest_map = _latest_validated_municipal_frame(root, source, str(outcome_id))
            observations = _series_observations(outcome_frame, source)
            geography_ids = sorted({item["geographyId"] for item in observations})
            neurological_sim = source == "SIM" and str(outcome_id) in {"alzheimer", "dementias_all"}
            available_metrics = ["crude_rate_per_100k", "count"]
            if neurological_sim:
                available_metrics.insert(0, "age_sex_standardized_rate_per_100k")
            catalog.append(
                {
                    "id": indicator_id,
                    "source": source,
                    "outcomeId": str(outcome_id),
                    "label": str(outcome_frame.iloc[0]["outcome_label"]),
                    "theme": _theme(str(outcome_id), sections),
                    "measure": source_definition["measure"],
                    "measureLabel": source_definition["measureLabel"],
                    "definition": source_definition["definition"],
                    "unit": source_definition["unit"],
                    "sourceLabel": source_definition["sourceLabel"],
                    "cidRanges": configured.get(str(outcome_id), {}).get("code_ranges", []),
                    "availableMetrics": available_metrics,
                    "geographyIds": geography_ids,
                    "yearStart": min(int(item["period"]) for item in observations),
                    "yearEnd": max(int(item["period"]) for item in observations),
                    "standardization": "age_sex_standardized_2022_and_crude_annual" if neurological_sim else "crude_only",
                    "geographyBasis": "residence",
                    "standardPopulation": "Brasil — Censo 2022" if neurological_sim else None,
                    "standardizationDimensions": ["age_group", "sex"] if neurological_sim else [],
                    "standardizedRateAvailability": "available_2022" if neurological_sim else "not_available",
                    "metricPeriod": {"age_sex_standardized_rate_per_100k": "2022"} if neurological_sim else {},
                    "unavailableReason": None,
                    "mapStatus": (
                        f"validated_{source.lower()}_{latest_map[2]}_municipal_residence_rates_crude"
                        if latest_map
                        else "context_only_pending_validated_municipal_rates"
                    ),
                    "profileAvailability": (
                        "available_2022_sim_age_sex"
                        if source == "SIM"
                        else "not_applicable_current_release"
                    ),
                    "allowsConclusion": (
                        "Descreve a frequência e a taxa registrada entre residentes e permite "
                        "comparações descritivas com os territórios disponíveis."
                    ),
                    "doesNotAllowConclusion": (
                        "Não mede causalidade ambiental, risco individual, incidência ou prevalência da doença."
                        if source == "SIM"
                        else "Não representa pessoas únicas, casos novos, incidência ou prevalência da doença."
                    ),
                    "synonyms": _indicator_synonyms(str(outcome_id), str(outcome_frame.iloc[0]["outcome_label"])),
                    "updatedAt": _utc_now(),
                    "methodologyUrl": f"/indicadores/{indicator_id}",
                }
            )
            series[indicator_id] = observations
    return catalog, series


def _indicator_synonyms(outcome_id: str, label: str) -> list[str]:
    common = {
        "lung": ["pulmão", "câncer de pulmão", "bronquios", "traqueia"],
        "pneumonia": ["pneumonia", "infecção pulmonar"],
        "acute_myocardial_infarction": ["infarto", "ataque cardíaco", "iam"],
        "all_malignant_neoplasms": ["câncer", "cancer", "neoplasias"],
        "alzheimer": ["alzheimer", "demência de alzheimer", "perda de memória"],
        "dementias_all": ["demência", "demências", "alzheimer", "perda de memória"],
    }
    return sorted({label.lower(), *common.get(outcome_id, [])})


def _municipal_map_payloads(root: Path, catalog: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for indicator in catalog:
        indicator_id = str(indicator["id"])
        outcome_id = str(indicator["outcomeId"])
        source = str(indicator.get("source"))
        standardized_path = root / "data" / "processed" / "sim_neurological_standardized_rates_2022.parquet"
        if source == "SIM" and outcome_id in {"alzheimer", "dementias_all"} and standardized_path.exists():
            frame = pd.read_parquet(standardized_path)
            values = []
            for row in frame.loc[frame["outcome_id"].eq(outcome_id)].itertuples(index=False):
                values.append(suppress_public_observation({
                    "source": source,
                    "outcomeId": outcome_id,
                    "geographyId": str(row.geography),
                    "period": "2022",
                    "metricKind": "age_sex_standardized_rate_per_100k",
                    "value": _finite_or_none(row.standardized_rate_per_100k),
                    "count": int(row.count),
                    "denominator": int(row.denominator),
                    "ciLow": _finite_or_none(row.standardized_ci_low_per_100k),
                    "ciHigh": _finite_or_none(row.standardized_ci_high_per_100k),
                    "dataStatus": "source_observed",
                    "periodStatus": "source_year_observed",
                    "manifestRef": "reports/quality/sim_neurological_standardized_manifest.json",
                    "geographyBasis": "residence",
                    "standardPopulation": str(row.standard_population),
                    "standardizationDimensions": ["age_group", "sex"],
                }))
            crude_path = root / "data" / "processed" / "sim_neurological_rates_annual.parquet"
            alternative_values: list[dict[str, Any]] = []
            if crude_path.exists():
                crude = pd.read_parquet(crude_path)
                crude = crude.loc[
                    crude["outcome_id"].eq(outcome_id) & crude["year"].eq(2024)
                    & crude["geography"].astype(str).str.match(r"^33\d{5}$")
                ]
                for row in crude.itertuples(index=False):
                    alternative_values.append(suppress_public_observation({
                        "source": source, "outcomeId": outcome_id, "geographyId": str(row.geography),
                        "period": "2024", "metricKind": "crude_rate_per_100k",
                        "value": _finite_or_none(row.rate_per_100k), "count": int(row.count),
                        "denominator": int(row.population), "ciLow": _finite_or_none(row.rate_ci_lower_per_100k),
                        "ciHigh": _finite_or_none(row.rate_ci_upper_per_100k), "dataStatus": "source_observed",
                        "periodStatus": str(row.period_status), "manifestRef": "reports/quality/sim_neurological_rates_manifest.json",
                        "geographyBasis": "residence",
                    }))
            payloads[indicator_id] = {
                "schemaVersion": "1.1.0",
                "indicatorId": indicator_id,
                "status": "validated_sim_2022_municipal_residence_rates_age_sex_standardized",
                "period": 2022,
                "metricKind": "age_sex_standardized_rate_per_100k",
                "values": values,
                "alternatives": [{"metricKind": "crude_rate_per_100k", "period": "2024", "values": alternative_values}],
                "note": "Taxa padronizada por idade e sexo pela população do Brasil no Censo 2022; células com contagem total <5 estão suprimidas.",
            }
            continue
        latest = _latest_validated_municipal_frame(root, source, outcome_id)
        if latest is None:
            payloads[indicator_id] = {
                "schemaVersion": "1.0.0",
                "indicatorId": indicator_id,
                "status": "context_only_pending_validated_municipal_rates",
                "values": [],
                "note": "A malha é contextual; taxas municipais só serão publicadas após validação por residência.",
            }
            continue
        frame, manifest_ref, year = latest
        selected = frame.loc[frame["outcome_id"].eq(outcome_id)]
        values: list[dict[str, Any]] = []
        for row in selected.itertuples(index=False):
            item = {
                "source": source,
                "outcomeId": outcome_id,
                "geographyId": str(row.municipality_code_ibge),
                "period": str(int(row.year)),
                "metricKind": "crude_rate_per_100k",
                "value": _finite_or_none(row.rate_per_100k),
                "count": int(row.count),
                "denominator": int(row.population),
                "ciLow": _finite_or_none(row.rate_ci_lower_per_100k),
                "ciHigh": _finite_or_none(row.rate_ci_upper_per_100k),
                "dataStatus": "provisional" if str(row.period_status) == "provisional" else "source_observed",
                "periodStatus": str(row.period_status),
                "manifestRef": manifest_ref,
            }
            values.append(suppress_public_observation(item))
        payloads[indicator_id] = {
            "schemaVersion": "1.0.0",
            "indicatorId": indicator_id,
            "status": (
                f"validated_sim_{year}_municipal_residence_rates_crude"
                if source == "SIM"
                else f"validated_sih_{year}_municipal_residence_rates_crude"
            ),
            "period": year,
            "values": values,
            "note": (
                f"Taxa bruta municipal de mortalidade SIM {year} por residência; células <5 suprimidas."
                if source == "SIM"
                else f"Taxa bruta municipal de internações SIH {year} por residência; AIHs são eventos e células <5 estão suprimidas."
            ),
        }
    return payloads


def _validated_municipal_frames(root: Path, source: str) -> list[tuple[pd.DataFrame, str]]:
    frames: list[tuple[pd.DataFrame, str]] = []
    prefix = source.lower()
    for path in sorted((root / "data" / "processed").glob(f"{prefix}_municipal_map_rates_*.parquet")):
        year_text = path.stem.rsplit("_", 1)[-1]
        if not year_text.isdigit():
            continue
        manifest_path = root / "reports" / "quality" / f"{prefix}_municipal_map_{year_text}_manifest.json"
        if not manifest_path.exists():
            continue
        try:
            status = str(json.loads(manifest_path.read_text(encoding="utf-8")).get("status", ""))
        except (OSError, json.JSONDecodeError):
            continue
        valid = status.startswith("validated_sim_") if source == "SIM" else status == "reconciled_with_annual_series"
        if valid:
            frames.append((pd.read_parquet(path), str(manifest_path.relative_to(root)).replace("\\", "/")))
    return frames


def _latest_validated_municipal_frame(root: Path, source: str, outcome_id: str | None = None) -> tuple[pd.DataFrame, str, str] | None:
    frames = _validated_municipal_frames(root, source)
    if outcome_id is not None:
        frames = [
            (frame.loc[frame["outcome_id"].eq(outcome_id)].copy(), manifest_ref)
            for frame, manifest_ref in frames
            if frame["outcome_id"].eq(outcome_id).any()
        ]
    if not frames:
        return None
    frame, manifest_ref = max(frames, key=lambda item: int(item[0]["year"].max()))
    return frame, manifest_ref, str(int(frame["year"].max()))


def _municipal_series_payloads(root: Path, catalog: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_source = {source: _validated_municipal_frames(root, source) for source in ("SIM", "SIH")}
    payloads: dict[str, dict[str, Any]] = {}
    for indicator in catalog:
        indicator_id = str(indicator["id"])
        outcome_id = str(indicator["outcomeId"])
        source = str(indicator["source"])
        observations: list[dict[str, Any]] = []
        frames = by_source[source]
        neurological_path = root / "data" / "processed" / "sim_neurological_rates_annual.parquet"
        if source == "SIM" and outcome_id in {"alzheimer", "dementias_all"} and neurological_path.exists():
            neurological = pd.read_parquet(neurological_path)
            neurological = neurological.loc[
                neurological["outcome_id"].eq(outcome_id)
                & neurological["geography"].astype(str).str.match(r"^33\d{5}$")
            ].rename(columns={"geography": "municipality_code_ibge"})
            frames = [(neurological, "reports/quality/sim_neurological_rates_manifest.json")]
        for frame, manifest_ref in frames:
            for row in frame.loc[frame["outcome_id"].eq(outcome_id)].itertuples(index=False):
                item = {
                    "source": source,
                    "outcomeId": outcome_id,
                    "geographyId": str(row.municipality_code_ibge),
                    "period": str(int(row.year)),
                    "metricKind": "crude_rate_per_100k",
                    "value": _finite_or_none(row.rate_per_100k),
                    "count": int(row.count),
                    "denominator": int(row.population),
                    "ciLow": _finite_or_none(row.rate_ci_lower_per_100k),
                    "ciHigh": _finite_or_none(row.rate_ci_upper_per_100k),
                    "dataStatus": "provisional" if str(row.period_status) == "provisional" else "source_observed",
                    "periodStatus": str(row.period_status),
                    "manifestRef": manifest_ref,
                    "geographyBasis": "residence",
                }
                observations.append(suppress_public_observation(item))
        standardized_path = root / "data" / "processed" / "sim_neurological_standardized_rates_2022.parquet"
        if source == "SIM" and outcome_id in {"alzheimer", "dementias_all"} and standardized_path.exists():
            standardized = pd.read_parquet(standardized_path)
            for row in standardized.loc[standardized["outcome_id"].eq(outcome_id)].itertuples(index=False):
                observations.append(suppress_public_observation({
                    "source": source,
                    "outcomeId": outcome_id,
                    "geographyId": str(row.geography),
                    "period": "2022",
                    "metricKind": "age_sex_standardized_rate_per_100k",
                    "value": _finite_or_none(row.standardized_rate_per_100k),
                    "count": int(row.count),
                    "denominator": int(row.denominator),
                    "ciLow": _finite_or_none(row.standardized_ci_low_per_100k),
                    "ciHigh": _finite_or_none(row.standardized_ci_high_per_100k),
                    "dataStatus": "source_observed",
                    "periodStatus": "source_year_observed",
                    "manifestRef": "reports/quality/sim_neurological_standardized_manifest.json",
                    "geographyBasis": "residence",
                    "standardPopulation": str(row.standard_population),
                    "standardizationDimensions": ["age_group", "sex"],
                }))
        periods = sorted({item["period"] for item in observations})
        payloads[indicator_id] = {
            "schemaVersion": "1.0.0",
            "indicatorId": indicator_id,
            "periods": periods,
            "observations": observations,
            "note": "Série municipal publicada somente para anos validados por residência; lacunas não são interpoladas.",
        }
    return payloads


def _profile_payload(root: Path, catalog: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    path = root / "data" / "processed" / "sim_municipal_age_sex_rates_2022.parquet"
    if not path.exists():
        return {}
    frame = pd.read_parquet(path)
    valid_ids = {item["id"] for item in catalog}
    payload: dict[str, list[dict[str, Any]]] = {}
    for outcome_id, group in frame.groupby("outcome_id", sort=True):
        indicator_id = _indicator_id("SIM", str(outcome_id))
        if indicator_id not in valid_ids:
            continue
        rows: list[dict[str, Any]] = []
        for row in group.itertuples(index=False):
            protected = str(row.suppression_status) != "published"
            not_applicable = str(row.suppression_status) == "not_applicable"
            item = {
                "municipalityCode": str(row.municipality_code_ibge),
                "indicatorId": indicator_id,
                "period": "2022",
                "ageGroup": str(row.age_group),
                "sex": str(row.sex),
                "count": None if protected else int(row.count),
                "denominator": None if not_applicable else int(row.population),
                "ratePer100k": None if protected else _finite_or_none(row.rate_per_100k),
                "ciLow": None if protected else _finite_or_none(row.rate_ci_lower_per_100k),
                "ciHigh": None if protected else _finite_or_none(row.rate_ci_upper_per_100k),
                "suppressionStatus": "not_applicable" if not_applicable else ("suppressed" if protected else "published"),
                "dataStatus": "source_observed",
                "manifestRef": "reports/quality/sim_municipal_age_sex_profiles_manifest.json",
            }
            rows.append(item)
        payload[indicator_id] = rows
    return payload


def _round_coordinates(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return round(float(value), 5)
    return [_round_coordinates(item) for item in value]


def _topology_geometry(geometry: dict[str, Any], arcs: list[Any]) -> dict[str, Any]:
    geometry_type = geometry["type"]
    coordinates = geometry["coordinates"]
    if geometry_type == "Polygon":
        refs = []
        for ring in coordinates:
            refs.append([len(arcs)])
            arcs.append(_round_coordinates(ring))
        return {"type": "Polygon", "arcs": refs}
    if geometry_type == "MultiPolygon":
        polygons = []
        for polygon in coordinates:
            refs = []
            for ring in polygon:
                refs.append([len(arcs)])
                arcs.append(_round_coordinates(ring))
            polygons.append(refs)
        return {"type": "MultiPolygon", "arcs": polygons}
    raise ValueError(f"unsupported IBGE geometry type: {geometry_type}")


def _build_topology(root: Path, acquire_geography: bool) -> dict[str, Any]:
    raw_path = root / "data" / "raw" / GEOGRAPHY_RAW_FILENAME
    if not raw_path.exists():
        if not acquire_geography:
            raise FileNotFoundError(
                f"official IBGE geography is missing: {raw_path}; rerun portal-data with --acquire-geography"
            )
        download_public_file(
            root,
            source_id="ibge_malha_municipal_rj",
            url=GEOGRAPHY_URL,
            filename=GEOGRAPHY_RAW_FILENAME,
            period="2024 reference mesh",
            territory="Rio de Janeiro; 92 municipalities",
        )
    raw_bytes = raw_path.read_bytes()
    if raw_bytes.startswith(b"\x1f\x8b"):
        raw_bytes = gzip.decompress(raw_bytes)
    payload = json.loads(raw_bytes.decode("utf-8"))
    if payload.get("type") != "FeatureCollection" or len(payload.get("features", [])) != 92:
        raise ValueError("IBGE RJ geography must contain exactly 92 municipality features")
    population_path = root / "data" / "processed" / "population_rj_municipality.parquet"
    population = pd.read_parquet(population_path)
    names = (
        population.sort_values("year")
        .drop_duplicates("municipality_code_ibge", keep="last")
        .set_index("municipality_code_ibge")["municipality_name"]
        .to_dict()
    )
    arcs: list[Any] = []
    geometries = []
    for feature in payload["features"]:
        code = str(feature.get("properties", {}).get("codarea", ""))
        geometry = _topology_geometry(feature["geometry"], arcs)
        geometry["id"] = code
        geometry["properties"] = {
            "code": code,
            "name": str(names.get(code, code)).replace(" - RJ", "").replace(" (RJ)", ""),
            "isVoltaRedonda": code == "3306305",
        }
        geometries.append(geometry)
    return {
        "type": "Topology",
        "objects": {"municipalities": {"type": "GeometryCollection", "geometries": geometries}},
        "arcs": arcs,
        "bbox": [-45.2, -23.4, -40.8, -20.7],
        "source": {
            "institution": "IBGE",
            "url": GEOGRAPHY_URL,
            "rawSha256": sha256_file(raw_path),
        },
    }


def _write_download_csv(path: Path, series: dict[str, list[dict[str, Any]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "indicatorId", "source", "outcomeId", "geographyId", "period", "metricKind",
        "value", "count", "denominator", "ciLow", "ciHigh", "dataStatus", "periodStatus",
        "suppressed", "manifestRef",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for indicator_id, observations in series.items():
            for observation in observations:
                writer.writerow({"indicatorId": indicator_id, **observation})


def _standardized_rest_of_rj(root: Path) -> dict[tuple[str, str], float]:
    rates_path = root / "data" / "processed" / "sim_municipal_age_sex_rates_2022.parquet"
    standard_path = root / "data" / "processed" / "population_age_sex_brazil_2022.parquet"
    if not rates_path.exists() or not standard_path.exists():
        return {}
    rates = pd.read_parquet(rates_path)
    rates = rates.loc[rates["outcome_id"].isin({"alzheimer", "dementias_all"})].copy()
    standard = pd.read_parquet(standard_path)
    result: dict[tuple[str, str], float] = {}
    for outcome_id, outcome in rates.groupby("outcome_id", sort=True):
        state = outcome.groupby(["age_group", "sex"], as_index=False)[["count", "population"]].sum()
        for municipality_code, city in outcome.groupby("municipality_code_ibge", sort=True):
            rest = state.merge(
                city[["age_group", "sex", "count", "population"]],
                on=["age_group", "sex"], suffixes=("_state", "_city"), validate="one_to_one",
            )
            rest["count"] = rest["count_state"] - rest["count_city"]
            rest["population"] = rest["population_state"] - rest["population_city"]
            rest["geography"] = "rest_of_rj"
            standardized = direct_standardized_rate(
                rest[["geography", "age_group", "sex", "count", "population"]], standard,
            )
            result[(str(outcome_id), str(municipality_code))] = float(standardized.iloc[0]["standardized_rate_per_100k"])
    return result


def _neurological_comparisons(root: Path) -> dict[str, list[dict[str, Any]]]:
    path = root / "data" / "processed" / "sim_neurological_rates_annual.parquet"
    if not path.exists():
        return {}
    frame = pd.read_parquet(path)
    output: dict[str, list[dict[str, Any]]] = {}
    for outcome_id in ("alzheimer", "dementias_all"):
        selected = frame.loc[frame["outcome_id"].eq(outcome_id)]
        state = selected.loc[selected["geography"].eq("rj_total")].set_index("year")
        rows: list[dict[str, Any]] = []
        for city in selected.loc[selected["geography"].astype(str).str.match(r"^33\d{5}$")].itertuples(index=False):
            state_row = state.loc[int(city.year)]
            rest_count = int(state_row["count"]) - int(city.count)
            rest_denominator = int(state_row["population"]) - int(city.population)
            rest = suppress_public_observation({
                "source": "SIM", "outcomeId": outcome_id,
                "geographyId": f"rest_of_rj_excluding_{city.geography}", "period": str(int(city.year)),
                "metricKind": "crude_rate_per_100k", "value": rest_count / rest_denominator * RATE_MULTIPLIER,
                "count": rest_count, "denominator": rest_denominator, "ciLow": None, "ciHigh": None,
                "dataStatus": "source_observed", "periodStatus": str(city.period_status),
                "manifestRef": "reports/quality/sim_neurological_rates_manifest.json", "geographyBasis": "residence",
            })
            rows.append({"municipalityCode": str(city.geography), "period": str(int(city.year)), "restOfState": rest, "brazil": None})
        output[_indicator_id("SIM", outcome_id)] = rows
    return output


def _municipality_summaries(
    catalog: list[dict[str, Any]],
    series: dict[str, list[dict[str, Any]]],
    municipal_series: dict[str, dict[str, Any]],
    root: Path | None = None,
) -> dict[str, Any]:
    indicators = {str(item["id"]): item for item in catalog}
    indicator_ids = sorted(indicators)
    municipality_codes = sorted({
        str(row["geographyId"])
        for indicator_id in indicator_ids
        for row in municipal_series[indicator_id]["observations"]
    })
    municipalities: dict[str, list[dict[str, Any]]] = {}
    standardized_rest = _standardized_rest_of_rj(root) if root else {}
    for municipality_code in municipality_codes:
        items: list[dict[str, Any]] = []
        for indicator_id in indicator_ids:
            indicator = indicators[indicator_id]
            rows = [
                row for row in municipal_series[indicator_id]["observations"]
                if row["geographyId"] == municipality_code
            ]
            standardized_rows = [row for row in rows if row.get("metricKind") == "age_sex_standardized_rate_per_100k"]
            latest = standardized_rows[0] if standardized_rows else (max(rows, key=lambda row: int(row["period"])) if rows else None)
            state = next((
                row for row in series[indicator_id]
                if latest and row["geographyId"] == "rj_total" and row["period"] == latest["period"]
            ), None)
            brazil = next((
                row for row in series[indicator_id]
                if latest and row["geographyId"] == "brazil_total" and row["period"] == latest["period"]
            ), None)
            if latest and latest.get("metricKind") == "age_sex_standardized_rate_per_100k":
                brazil = None
            rest_value = None
            if latest and latest.get("metricKind") == "age_sex_standardized_rate_per_100k" and not latest["suppressed"]:
                rest_value = standardized_rest.get((str(indicator["outcomeId"]), municipality_code))
            elif latest and state and not latest["suppressed"] and latest["count"] is not None:
                denominator = state["denominator"] - latest["denominator"]
                count = state["count"] - latest["count"]
                if denominator > 0 and count >= 0:
                    rest_value = count / denominator * RATE_MULTIPLIER
            items.append({
                "indicatorId": indicator_id,
                "period": latest["period"] if latest else None,
                "metricKind": latest.get("metricKind", "crude_rate_per_100k") if latest else None,
                "value": latest["value"] if latest else None,
                "count": latest["count"] if latest else None,
                "unit": indicator["unit"],
                "dataStatus": latest["dataStatus"] if latest else "unavailable",
                "suppressionStatus": "suppressed" if latest and latest["suppressed"] else "published" if latest else "unavailable",
                "restOfStateValue": _finite_or_none(rest_value),
                "brazilValue": brazil["value"] if brazil and not brazil["suppressed"] else None,
                "comparisonAvailable": rest_value is not None,
                "unavailableReason": latest.get("suppressionReason") if latest and latest["suppressed"] else None,
            })
        municipalities[municipality_code] = items
    return municipalities


def build_portal_data(
    root: Path,
    release_id: str = "technical-beta",
    acquire_geography: bool = False,
) -> tuple[Path, Path]:
    output_root = root / "site" / "public" / "data"
    catalog, series = _build_catalog_and_series(root)
    if not catalog:
        raise ValueError("no validated rate artifacts are available for portal publication")
    profiles = _profile_payload(root, catalog)
    maps = _municipal_map_payloads(root, catalog)
    municipal_series = _municipal_series_payloads(root, catalog)
    for indicator in catalog:
        indicator_id = str(indicator["id"])
        municipal_payload = municipal_series[indicator_id]
        periods = municipal_payload["periods"]
        public_rows = [item for item in municipal_payload["observations"] if item.get("value") is not None and not item.get("suppressed")]
        public_codes = {item["geographyId"] for item in public_rows}
        provisional_periods = sorted({item["period"] for item in municipal_payload["observations"] if item.get("dataStatus") == "provisional"})
        missing_periods: list[str] = []
        if periods:
            available = {int(period) for period in periods}
            missing_periods = [str(year) for year in range(min(available), max(available) + 1) if year not in available]
        indicator["municipalPeriods"] = periods
        indicator["geographicCoverage"] = {
            "municipalityCount": 92,
            "publishableMunicipalityCount": len(public_codes),
        }
        indicator["temporalCoverage"] = {
            "firstPeriod": periods[0] if periods else None,
            "lastPeriod": periods[-1] if periods else None,
            "periods": periods,
            "missingPeriods": missing_periods,
            "provisionalPeriods": provisional_periods,
        }
        profile_rows = profiles.get(indicator_id, [])
        indicator["profileCoverage"] = {
            "status": "available" if profile_rows else "unavailable",
            "municipalityCount": 92 if profile_rows else 0,
            "publishableMunicipalityCount": len({item["municipalityCode"] for item in profile_rows if item["suppressionStatus"] == "published"}),
            "periods": sorted({item["period"] for item in profile_rows}),
            "ageGroups": ["<1", "1-4", "5-14", "15-24", "25-44", "45-64", "65-74", "75+"] if profile_rows else [],
            "sexes": ["masculino", "feminino"] if profile_rows else [],
            "unavailableReason": None if profile_rows else "municipal_profile_not_validated_for_source",
        }
        indicator["comparisonAvailability"] = {
            "restOfState": True,
            "brazil": "brazil_total" in indicator["geographyIds"] and indicator["theme"] != "neurological",
            "reason": "national_standardized_equivalent_unavailable" if indicator["theme"] == "neurological" else (None if "brazil_total" in indicator["geographyIds"] else "national_equivalent_unavailable"),
        }
        map_metric = str(maps[indicator_id].get("metricKind", "crude_rate_per_100k"))
        values = [
            item["value"] for item in municipal_payload["observations"]
            if item.get("value") is not None and item.get("metricKind") == map_metric
        ]
        maps[indicator_id]["mapScale"] = {
            "domain": [min(values), max(values)] if values else None,
            "method": "fixed_indicator_metric",
            "unit": map_metric,
            "temporalPolicy": "comparable_across_available_periods",
        }
    topology = _build_topology(root, acquire_geography)
    summaries = _municipality_summaries(catalog, series, municipal_series, root=root)
    neurological_comparisons = _neurological_comparisons(root)

    _write_json(output_root / "catalog.json", {
        "schemaVersion": "1.1.0",
        "geographies": GEOGRAPHY_LABELS,
        "indicators": catalog,
        "futureCapabilities": ["air_quality", "meteorology", "neighborhoods"],
        "discovery": {"generatedAt": _utc_now(), "municipalityCount": 92},
    })
    for indicator in catalog:
        indicator_id = indicator["id"]
        _write_json(output_root / "series" / f"{indicator_id}.json", {
            "schemaVersion": "1.0.0",
            "indicatorId": indicator_id,
            "observations": series[indicator_id],
        })
        _write_json(output_root / "profiles" / f"{indicator_id}.json", {
            "schemaVersion": "1.0.0",
            "indicatorId": indicator_id,
            "observations": profiles.get(indicator_id, []),
        })
        _write_json(output_root / "maps" / "rj" / f"{indicator_id}.json", maps[indicator_id])
        _write_json(output_root / "municipal-series" / f"{indicator_id}.json", municipal_series[indicator_id])
        if indicator_id in neurological_comparisons:
            _write_json(output_root / "comparisons" / f"{indicator_id}.json", {
                "schemaVersion": "1.0.0", "indicatorId": indicator_id,
                "comparisons": neurological_comparisons[indicator_id],
            })
    _write_json(output_root / "geography" / "rj.topojson", topology)
    for municipality_code, items in summaries.items():
        _write_json(output_root / "municipality-summaries" / f"{municipality_code}.json", {
            "schemaVersion": "1.0.0",
            "generatedAt": _utc_now(),
            "municipalityCode": municipality_code,
            "items": items,
        })
    _write_download_csv(output_root / "downloads" / "series-publicas.csv", series)

    artifacts = []
    for path in sorted(output_root.rglob("*")):
        if path.is_file() and path.name != "release.json":
            artifacts.append({
                "path": str(path.relative_to(output_root)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    denominator_manifest_path = root / "reports" / "quality" / "population_denominator_manifest.json"
    missing_denominator_years = [2010, 2023]
    if denominator_manifest_path.exists():
        try:
            denominator_manifest = json.loads(denominator_manifest_path.read_text(encoding="utf-8"))
            missing_denominator_years = [
                int(year) for year in denominator_manifest.get("missing_years", missing_denominator_years)
            ]
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            # Keep a conservative fallback if an older/incomplete manifest is present.
            pass
    signoff_path = root / "reports" / "reviews" / "release_signoff.json"
    review_signoff: dict[str, Any] = {}
    if signoff_path.exists():
        try:
            candidate = json.loads(signoff_path.read_text(encoding="utf-8"))
            if candidate.get("releaseId") == release_id:
                review_signoff = candidate
        except (OSError, json.JSONDecodeError, AttributeError):
            review_signoff = {}
    accessibility_audit_path = root / "reports" / "quality" / "portal_accessibility_audit.json"
    accessibility_audit: dict[str, Any] = {}
    if accessibility_audit_path.exists():
        try:
            accessibility_audit = json.loads(accessibility_audit_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, AttributeError):
            accessibility_audit = {}
    accessibility_revalidated = accessibility_audit.get("status") == "statewide_manual_validation_approved"
    publication_gate = {
        "epidemiologyReview": review_signoff.get("epidemiologyReview", {}).get("status", "pending"),
        "accessibilityReview": (
            review_signoff.get("accessibilityReview", {}).get("status", "pending")
            if accessibility_revalidated else "pending"
        ),
        "provenanceReview": "generated",
    }
    release_status = (
        "public_release_ready"
        if publication_gate["epidemiologyReview"] == "approved"
        and publication_gate["accessibilityReview"] == "approved"
        else "technical_beta_not_for_public_release"
    )
    release = {
        "schemaVersion": "1.0.0",
        "releaseId": release_id,
        "generatedAt": _utc_now(),
        "status": release_status,
        "smallCellThreshold": SMALL_CELL_THRESHOLD,
        "primaryComparator": "rest_of_rj_excluding_selected_municipality",
        "secondaryComparator": "brazil_total",
        "publicationGate": publication_gate,
        "reviewSignoff": review_signoff,
        "coverage": {
            "indicatorCount": len(catalog),
            "respiratoryStart": 2008,
            "cardiovascularStart": 2008,
            "cardiorespiratoryStart": 2008,
            "cancerStart": 2011,
            "latestObservedYear": max(item["yearEnd"] for item in catalog),
            "missingDenominatorYears": missing_denominator_years,
        },
        "notes": [
            "No causal conclusion is authorized by this release.",
            "SIH hospitalizations are events/AIHs, not unique people or new cases.",
            "SIM cancer mortality is not population incidence.",
            "SIM 2022 municipal mortality rates and reconciled SIH 2022 municipal AIH rates are published only for validated residence cells; neither layer is an incidence estimate.",
        ],
        "artifacts": artifacts,
    }
    release_path = output_root / "release.json"
    _write_json(release_path, release)
    return output_root, release_path
