from pathlib import Path

import pandas as pd

from vr_saude.outcomes import _definitions, _matches_cid
from vr_saude.sia import build_sia_alzheimer_production
from vr_saude.sih_municipal_map import _diagnostic_query
from vr_saude.standardization import direct_standardized_rate


ROOT = Path(__file__).resolve().parents[1]


def test_alzheimer_and_dementia_code_families_are_distinct() -> None:
    codes = pd.Series(["G300", "G309", "F000", "F002", "F019", "F029", "F039", "G310"])
    assert _matches_cid(codes, ["G30", "F00.0-F00.2"]).tolist() == [True, True, True, True, False, False, False, False]
    assert _matches_cid(codes, ["G30", "F00-F03"]).tolist() == [True, True, True, True, True, True, True, False]


def test_neurological_definitions_are_configured_for_sim_and_sih() -> None:
    ids = {item["id"] for item in _definitions(ROOT, "SIM")}
    assert {"alzheimer", "dementias_all"} <= ids


def test_sih_tabnet_official_groups_are_selected_without_html_closing_tags() -> None:
    definition = (ROOT / "data" / "interim" / "sih_definition.html").read_text(encoding="latin1")
    assert _diagnostic_query(definition, "alzheimer") == ("lista", ["146"])
    assert _diagnostic_query(definition, "dementias_all") == ("lista", ["132", "146"])


def test_direct_standardization_uses_one_common_standard() -> None:
    rates = pd.DataFrame([
        {"geography": "city_a", "age_group": "65-74", "sex": "feminino", "count": 10, "population": 1000},
        {"geography": "city_a", "age_group": "75+", "sex": "feminino", "count": 20, "population": 1000},
        {"geography": "city_b", "age_group": "65-74", "sex": "feminino", "count": 20, "population": 1000},
        {"geography": "city_b", "age_group": "75+", "sex": "feminino", "count": 10, "population": 1000},
    ])
    standard = pd.DataFrame([
        {"age_group": "65-74", "sex": "feminino", "population": 3},
        {"age_group": "75+", "sex": "feminino", "population": 1},
    ])
    result = direct_standardized_rate(rates, standard)
    city_a = result.loc[result["geography"].eq("city_a"), "standardized_rate_per_100k"].item()
    city_b = result.loc[result["geography"].eq("city_b"), "standardized_rate_per_100k"].item()
    assert city_a == 1_250
    assert city_b == 1_750


def test_sia_is_unavailable_without_validated_diagnostic_dimension(tmp_path) -> None:
    output, manifest, report = build_sia_alzheimer_production(tmp_path)
    assert output is None
    assert "unavailable" in manifest.read_text(encoding="utf-8")
    assert "não será publicada" in report.read_text(encoding="utf-8")


def test_generated_sim_neurological_series_covers_all_rj_municipalities() -> None:
    frame = pd.read_parquet(ROOT / "data" / "processed" / "sim_neurological_rates_annual.parquet")
    municipal = frame.loc[frame["geography"].astype(str).str.match(r"^33\d{5}$")]
    assert municipal["geography"].nunique() == 92
    assert municipal["year"].min() == 2010
    assert municipal["year"].max() == 2024


def test_public_comparison_uses_aggregated_rj_numerator_and_denominator() -> None:
    rates = pd.read_parquet(ROOT / "data" / "processed" / "sim_neurological_rates_annual.parquet")
    city = rates.loc[
        rates["geography"].eq("3300100")
        & rates["outcome_id"].eq("alzheimer")
        & rates["year"].eq(2022)
    ].iloc[0]
    state = rates.loc[
        rates["geography"].eq("rj_total")
        & rates["outcome_id"].eq("alzheimer")
        & rates["year"].eq(2022)
    ].iloc[0]
    expected_count = int(state["count"] - city["count"])
    expected_denominator = int(state["population"] - city["population"])
    # Read the JSON directly to avoid normalizing the nested comparison contract.
    import json
    payload = json.loads((ROOT / "site" / "public" / "data" / "comparisons" / "sim-alzheimer.json").read_text(encoding="utf-8"))
    item = next(row for row in payload["comparisons"] if row["municipalityCode"] == "3300100" and row["period"] == "2022")
    assert item["restOfState"]["count"] == expected_count
    assert item["restOfState"]["denominator"] == expected_denominator
