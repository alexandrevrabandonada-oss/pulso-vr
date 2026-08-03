import json

import pandas as pd

from vr_saude.portal_data import _municipal_map_payloads, _municipal_series_payloads, _topology_geometry, suppress_public_observation


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
