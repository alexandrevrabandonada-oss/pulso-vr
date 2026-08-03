import json
from pathlib import Path

import pandas as pd

from vr_saude.portal_data import _municipal_map_payloads, _municipal_series_payloads, _municipality_summaries, _topology_geometry, suppress_public_observation


ROOT = Path(__file__).resolve().parents[1]


def test_publication_suppresses_small_cells_before_frontend() -> None:
    observation = {
        "value": 1.4,
        "count": 4,
        "ciLow": 0.4,
        "ciHigh": 3.0,
        "denominator": 100_000,
    }
    published = suppress_public_observation(observation)
    assert published["suppressed"] is True
    assert published["suppressionReason"] == "small_cell_lt_5"
    assert published["value"] is None
    assert published["count"] is None
    assert published["ciLow"] is None
    assert published["ciHigh"] is None
    assert published["denominator"] == 100_000


def test_publication_keeps_non_small_cell_values() -> None:
    observation = {"value": 2.0, "count": 5, "ciLow": 1.0, "ciHigh": 3.0}
    published = suppress_public_observation(observation)
    assert published["suppressed"] is False
    assert published["count"] == 5


def test_topology_conversion_keeps_polygon_as_arc_reference() -> None:
    arcs: list[object] = []
    converted = _topology_geometry(
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        arcs,
    )
    assert converted == {"type": "Polygon", "arcs": [[0]]}
    assert arcs == [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]]]


def test_municipal_series_uses_only_validated_years_and_suppresses_small_cells(tmp_path) -> None:
    processed = tmp_path / "data" / "processed"
    quality = tmp_path / "reports" / "quality"
    processed.mkdir(parents=True)
    quality.mkdir(parents=True)
    frame = pd.DataFrame([{
        "municipality_code_ibge": "3300100", "outcome_id": "lung", "year": 2022,
        "count": 4, "population": 100_000, "rate_per_100k": 4.0,
        "rate_ci_lower_per_100k": 1.0, "rate_ci_upper_per_100k": 8.0,
        "period_status": "source_year_observed",
    }])
    frame.to_parquet(processed / "sim_municipal_map_rates_2022.parquet", index=False)
    (quality / "sim_municipal_map_2022_manifest.json").write_text(
        json.dumps({"status": "validated_sim_2022_municipal_residence_rates_crude"}), encoding="utf-8"
    )
    payload = _municipal_series_payloads(tmp_path, [{"id": "sim-lung", "outcomeId": "lung", "source": "SIM"}])
    assert payload["sim-lung"]["periods"] == ["2022"]
    assert payload["sim-lung"]["observations"][0]["count"] is None
    assert payload["sim-lung"]["observations"][0]["suppressed"] is True


def test_municipal_map_uses_latest_validated_year(tmp_path) -> None:
    processed = tmp_path / "data" / "processed"
    quality = tmp_path / "reports" / "quality"
    processed.mkdir(parents=True)
    quality.mkdir(parents=True)
    for year in (2022, 2024):
        frame = pd.DataFrame([{
            "municipality_code_ibge": "3300100", "outcome_id": "lung", "year": year,
            "count": 5, "population": 100_000, "rate_per_100k": 5.0,
            "rate_ci_lower_per_100k": 1.0, "rate_ci_upper_per_100k": 9.0,
            "period_status": "source_year_observed",
        }])
        frame.to_parquet(processed / f"sim_municipal_map_rates_{year}.parquet", index=False)
        (quality / f"sim_municipal_map_{year}_manifest.json").write_text(
            json.dumps({"status": f"validated_sim_{year}_municipal_residence_rates_crude"}), encoding="utf-8"
        )
    payload = _municipal_map_payloads(tmp_path, [{"id": "sim-lung", "outcomeId": "lung", "source": "SIM"}])
    assert payload["sim-lung"]["period"] == "2024"
    assert payload["sim-lung"]["values"][0]["period"] == "2024"


def test_municipality_summary_is_lightweight_dynamic_and_suppression_safe() -> None:
    ids = ["sih-pneumonia", "sim-lung", "sim-all-malignant-neoplasms", "sim-acute-myocardial-infarction"]
    catalog = [{"id": indicator_id, "unit": "taxa por 100 mil"} for indicator_id in ids]
    municipal = {}
    aggregate = {}
    for indicator_id in ids:
        protected = indicator_id == "sim-lung"
        municipal[indicator_id] = {"observations": [{
            "geographyId": "3300100", "period": "2022", "value": None if protected else 10.0,
            "count": None if protected else 10, "denominator": 100_000, "dataStatus": "source_observed",
            "suppressed": protected, "suppressionReason": "small_cell_lt_5" if protected else None,
        }]}
        aggregate[indicator_id] = [{
            "geographyId": "rj_total", "period": "2022", "value": 20.0,
            "count": 200, "denominator": 1_000_000, "dataStatus": "source_observed", "suppressed": False,
        }]
    payload = _municipality_summaries(catalog, aggregate, municipal)
    items = payload["3300100"]
    published = next(item for item in items if item["indicatorId"] == "sih-pneumonia")
    protected = next(item for item in items if item["indicatorId"] == "sim-lung")
    assert round(published["restOfStateValue"], 2) == 21.11
    assert protected["value"] is None and protected["count"] is None
    assert protected["restOfStateValue"] is None


def test_published_municipality_summaries_cover_state_without_protected_leaks() -> None:
    paths = sorted((ROOT / "site" / "public" / "data" / "municipality-summaries").glob("*.json"))
    assert len(paths) == 92
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["municipalityCode"] == path.stem
        assert len(payload["items"]) == 45
        for item in payload["items"]:
            if item["suppressionStatus"] == "suppressed":
                assert item["value"] is None
                assert item["count"] is None
                assert item["restOfStateValue"] is None
