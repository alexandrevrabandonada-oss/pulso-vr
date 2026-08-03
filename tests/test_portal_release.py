from __future__ import annotations

import json

from vr_saude.portal_release import assess_portal_release


def _write_json(path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_portal_preflight_detects_missing_map_profiles_and_brazil_sih(tmp_path) -> None:
    data = tmp_path / "site" / "public" / "data"
    indicator = {
        "id": "sih-resp-all",
        "source": "SIH",
        "mapStatus": "context_only_pending_validated_municipal_rates",
    }
    profile_indicator = {
        "id": "sim-resp-all",
        "source": "SIM",
        "mapStatus": "context_only_pending_validated_municipal_rates",
    }
    observation = {
        "source": "SIH",
        "outcomeId": "resp_all",
        "geographyId": "volta_redonda",
        "period": "2024",
        "metricKind": "crude_rate_per_100k",
        "value": 1.0,
        "count": 10,
        "denominator": 100000,
        "ciLow": 0.5,
        "ciHigh": 2.0,
        "dataStatus": "source_observed",
        "periodStatus": "complete_annual",
        "suppressed": False,
        "manifestRef": "reports/quality/example.json",
    }
    _write_json(data / "release.json", {
        "releaseId": "technical-beta",
        "status": "technical_beta_not_for_public_release",
        "publicationGate": {"epidemiologyReview": "pending"},
        "coverage": {"missingDenominatorYears": [2010, 2023]},
        "artifacts": [],
    })
    sim_observation = {**observation, "source": "SIM", "outcomeId": "resp_all", "geographyId": "brazil_total"}
    _write_json(data / "catalog.json", {"indicators": [indicator, profile_indicator]})
    _write_json(data / "series" / "sih-resp-all.json", {"observations": [observation]})
    _write_json(data / "profiles" / "sih-resp-all.json", {"observations": []})
    _write_json(data / "maps" / "rj" / "sih-resp-all.json", {"status": indicator["mapStatus"], "values": []})
    _write_json(data / "series" / "sim-resp-all.json", {"observations": [sim_observation]})
    _write_json(data / "profiles" / "sim-resp-all.json", {"observations": []})
    _write_json(data / "maps" / "rj" / "sim-resp-all.json", {"status": profile_indicator["mapStatus"], "values": []})
    (tmp_path / "metadata").mkdir(parents=True)
    (tmp_path / "metadata" / "source_catalog.csv").write_text(
        "source_id,status\nexample,verified\n", encoding="utf-8"
    )

    report = assess_portal_release(tmp_path)
    finding_ids = {item["id"] for item in report["findings"]}
    assert report["publicationAllowed"] is False
    assert {"release-not-public", "review-gates-pending", "municipal-map-not-publishable", "sih-brazil-comparator-missing", "profiles-incomplete"} <= finding_ids
    assert report["summary"]["missingDenominatorYears"] == [2010, 2023]


def test_portal_preflight_accepts_complete_small_safe_fixture(tmp_path) -> None:
    data = tmp_path / "site" / "public" / "data"
    indicator = {"id": "sim-resp-all", "source": "SIM", "mapStatus": "validated"}
    observation = {
        "source": "SIM",
        "outcomeId": "resp_all",
        "geographyId": "brazil_total",
        "period": "2024",
        "metricKind": "crude_rate_per_100k",
        "value": 1.0,
        "count": 10,
        "denominator": 100000,
        "ciLow": 0.5,
        "ciHigh": 2.0,
        "dataStatus": "source_observed",
        "periodStatus": "complete_annual",
        "suppressed": False,
        "manifestRef": "reports/quality/example.json",
    }
    _write_json(data / "release.json", {
        "releaseId": "public",
        "status": "public_release_ready",
        "publicationGate": {"epidemiologyReview": "approved"},
        "coverage": {"missingDenominatorYears": []},
        "artifacts": [],
    })
    _write_json(data / "catalog.json", {"indicators": [indicator]})
    _write_json(data / "series" / "sim-resp-all.json", {"observations": [observation]})
    _write_json(data / "profiles" / "sim-resp-all.json", {"observations": [observation]})
    _write_json(data / "maps" / "rj" / "sim-resp-all.json", {"status": "validated", "values": [observation]})
    (tmp_path / "metadata").mkdir(parents=True)
    (tmp_path / "metadata" / "source_catalog.csv").write_text(
        "source_id,status\nexample,verified\n", encoding="utf-8"
    )

    report = assess_portal_release(tmp_path)
    assert report["publicationAllowed"] is True
    assert report["summary"]["blockerCount"] == 0


def test_portal_preflight_detects_download_suppression_leak(tmp_path) -> None:
    data = tmp_path / "site" / "public" / "data"
    indicator = {"id": "sim-resp-all", "source": "SIM", "mapStatus": "validated"}
    observation = {
        "source": "SIM", "outcomeId": "resp_all", "geographyId": "brazil_total",
        "period": "2024", "metricKind": "crude_rate_per_100k", "value": 1.0,
        "count": 10, "denominator": 100000, "ciLow": 0.5, "ciHigh": 2.0,
        "dataStatus": "source_observed", "periodStatus": "complete_annual",
        "suppressed": False, "manifestRef": "reports/quality/example.json",
    }
    _write_json(data / "release.json", {
        "releaseId": "public", "status": "public_release_ready",
        "publicationGate": {"epidemiologyReview": "approved"},
        "coverage": {"missingDenominatorYears": []}, "artifacts": [],
    })
    _write_json(data / "catalog.json", {"indicators": [indicator]})
    _write_json(data / "series" / "sim-resp-all.json", {"observations": [observation]})
    _write_json(data / "profiles" / "sim-resp-all.json", {"observations": [observation]})
    _write_json(data / "maps" / "rj" / "sim-resp-all.json", {"status": "validated", "values": [observation]})
    (data / "downloads").mkdir(parents=True)
    (data / "downloads" / "series-publicas.csv").write_text(
        "outcomeId,period,value,count,ciLow,ciHigh,suppressed\nresp_all,2024,2.1,,,,true\n",
        encoding="utf-8",
    )
    (tmp_path / "metadata").mkdir(parents=True)
    (tmp_path / "metadata" / "source_catalog.csv").write_text(
        "source_id,status\nexample,verified\n", encoding="utf-8"
    )

    report = assess_portal_release(tmp_path)
    assert report["publicationAllowed"] is False
    assert report["summary"]["downloadSuppressionLeaks"] == 1
    assert "download-suppression-leak" in {item["id"] for item in report["findings"]}
