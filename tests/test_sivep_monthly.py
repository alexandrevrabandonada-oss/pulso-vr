import pandas as pd

from vr_saude.sivep_monthly import _sivep_geography


def test_sivep_geography_uses_residence_and_excludes_vr_from_rest() -> None:
    codes = pd.Series(["330630", "330455", "355030", "invalid"])
    assert _sivep_geography(codes).tolist() == [
        "volta_redonda",
        "rest_of_rj_excluding_vr",
        "outside_rj",
        "outside_rj",
    ]
