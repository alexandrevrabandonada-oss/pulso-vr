import pandas as pd

from vr_saude.sivep_monthly import _period_status, _sivep_geography


def test_sivep_geography_uses_residence_and_excludes_vr_from_rest() -> None:
    codes = pd.Series(["330630", "330455", "355030", "invalid"])
    assert _sivep_geography(codes).tolist() == [
        "volta_redonda",
        "rest_of_rj_excluding_vr",
        "outside_rj",
        "outside_rj",
    ]


def test_sivep_period_status_marks_partial_2026() -> None:
    assert _period_status(2025) == "provisional_2025"
    assert _period_status(2026) == "provisional_partial_2026"
    assert _period_status(2024) == "surveillance_versioned"
