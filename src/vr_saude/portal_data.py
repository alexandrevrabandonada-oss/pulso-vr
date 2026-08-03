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
            "sobre Mortalidade. Mortalidade por câncer não representa incidência."
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
        observation = {
            "source": source,
            "outcomeId": str(row.outcome_id),
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
                "reports/quality/respiratory_rates_manifest.json"
                if source == "SIH"
                else "reports/quality/sim_mortality_rates_manifest.json"
            ),
        }
        observations.append(suppress_public_observation(observation))
    return observations


def _indicator_id(source: str, outcome_id: str) -> str:
    return f"{source.lower()}-{outcome_id.replace('_', '-')}"


def _theme(outcome_id: str, outcome_config: dict[str, set[str]]) -> str:
    for theme in ("respiratory", "cardiovascular", "cardiorespiratory", "cancer"):
        if outcome_id in outcome_config[theme]:
            return theme
    raise ValueError(f"outcome is not assigned to a portal theme: {outcome_id}")


def _configured_outcomes(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, set[str]]]:
    config = load_config("outcomes.yml", root)
    by_id: dict[str, dict[str, Any]] = {}
    sections = {"respiratory": set(), "cardiovascular": set(), "cardiorespiratory": set(), "cancer": set()}
    for section in sections:
        for item in config.get(section, []):
            by_id[item["id"]] = item
            sections[section].add(item["id"])
    return by_id, sections


def _build_catalog_and_series(root: Path) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    configured, sections = _configured_outcomes(root)
    sources = [
        ("SIH", root / "data" / "processed" / "respiratory_rates_annual.parquet"),
        ("SIM", root / "data" / "processed" / "sim_mortality_rates_sample.parquet"),
    ]
    catalog: list[dict[str, Any]] = []
    series: dict[str, list[dict[str, Any]]] = {}
    for source, path in sources:
        if not path.exists():
            continue
        frame = pd.read_parquet(path)
        for outcome_id, outcome_frame in frame.groupby("outcome_id", sort=True):
            source_definition = SOURCE_DEFINITIONS[source]
            indicator_id = _indicator_id(source, str(outcome_id))
            latest_map = _latest_validated_municipal_frame(root, source, str(outcome_id))
            observations = _series_observations(outcome_frame, source)
            geography_ids = sorted({item["geographyId"] for item in observations})
            available_metrics = ["crude_rate_per_100k", "count"]
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
                    "standardization": "crude_only",
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
                        "Não mede causalidade ambiental, risco individual ou incidência de câncer."
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
    }
    return sorted({label.lower(), *common.get(outcome_id, [])})


def _municipal_map_payloads(root: Path, catalog: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for indicator in catalog:
        indicator_id = str(indicator["id"])
        outcome_id = str(indicator["outcomeId"])
        source = str(indicator.get("source"))
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
        for frame, manifest_ref in by_source[source]:
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
                }
                observations.append(suppress_public_observation(item))
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
    path = root / "data" / "processed" / "sim_mortality_age_sex_rates_2022.parquet"
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
            item = {
                "source": "SIM",
                "outcomeId": str(outcome_id),
                "geographyId": str(row.geography),
                "period": "2022",
                "ageGroup": str(row.age_group),
                "sex": str(row.sex),
                "metricKind": "age_sex_specific_crude_rate_per_100k",
                "value": _finite_or_none(row.rate_per_100k),
                "count": int(row.count),
                "denominator": int(row.population),
                "ciLow": _finite_or_none(row.rate_ci_lower_per_100k),
                "ciHigh": _finite_or_none(row.rate_ci_upper_per_100k),
                "dataStatus": "source_observed",
                "periodStatus": str(row.period_status),
                "manifestRef": "reports/quality/sim_age_sex_rates_manifest.json",
            }
            rows.append(suppress_public_observation(item))
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
        profile_geographies = sorted({item["geographyId"] for item in profile_rows})
        indicator["profileCoverage"] = {
            "status": "pilot" if profile_rows else "unavailable",
            "geographies": profile_geographies,
            "periods": sorted({item["period"] for item in profile_rows}),
            "dimensions": ["age", "sex"] if profile_rows else [],
        }
        indicator["comparisonAvailability"] = {
            "restOfState": True,
            "brazil": "brazil_total" in indicator["geographyIds"],
            "reason": None if "brazil_total" in indicator["geographyIds"] else "national_equivalent_unavailable",
        }
        values = [item["value"] for item in municipal_payload["observations"] if item.get("value") is not None]
        maps[indicator_id]["mapScale"] = {
            "domain": [min(values), max(values)] if values else None,
            "method": "fixed_indicator_metric",
            "unit": "crude_rate_per_100k",
            "temporalPolicy": "comparable_across_available_periods",
        }
    topology = _build_topology(root, acquire_geography)

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
    _write_json(output_root / "geography" / "rj.topojson", topology)
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
    publication_gate = {
        "epidemiologyReview": review_signoff.get("epidemiologyReview", {}).get("status", "pending"),
        "accessibilityReview": review_signoff.get("accessibilityReview", {}).get("status", "pending"),
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
