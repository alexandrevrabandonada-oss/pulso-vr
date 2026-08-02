import pandas as pd

from vr_saude.outcomes import _matches_cid, _sivep_age_groups


def test_matches_cid_range_without_confusing_adjacent_chapters() -> None:
    codes = pd.Series(["J189", "J440", "C340", "I10"])
    assert _matches_cid(codes, ["J12-J18"]).tolist() == [True, False, False, False]
    assert _matches_cid(codes, ["J40-J44"]).tolist() == [False, True, False, False]


def test_sivep_age_units_become_broad_age_groups() -> None:
    ages = pd.Series([2, 6, 40])
    units = pd.Series(["2", "3", "3"])
    assert _sivep_age_groups(ages, units).tolist() == ["<1", "5-14", "25-44"]
