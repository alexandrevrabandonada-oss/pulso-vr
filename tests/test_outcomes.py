import pandas as pd

from vr_saude.outcomes import _geography, _matches_cid, _sivep_age_groups


def test_matches_cid_range_without_confusing_adjacent_chapters() -> None:
    codes = pd.Series(["J189", "J440", "C340", "I10", "I219", "I500", "J189"])
    assert _matches_cid(codes, ["J12-J18"]).tolist() == [True, False, False, False, False, False, True]
    assert _matches_cid(codes, ["J40-J44"]).tolist() == [False, True, False, False, False, False, False]
    assert _matches_cid(codes, ["I20-I25"]).tolist() == [False, False, False, False, True, False, False]
    assert _matches_cid(codes, ["I50"]).tolist() == [False, False, False, False, False, True, False]


def test_matches_three_character_category_and_subcategories() -> None:
    codes = pd.Series(["C50", "C509", "C61", "C619", "C51"])
    assert _matches_cid(codes, ["C50"]).tolist() == [True, True, False, False, False]
    assert _matches_cid(codes, ["C61"]).tolist() == [False, False, True, True, False]


def test_sivep_age_units_become_broad_age_groups() -> None:
    ages = pd.Series([2, 6, 40])
    units = pd.Series(["2", "3", "3"])
    assert _sivep_age_groups(ages, units).tolist() == ["<1", "5-14", "25-44"]


def test_geography_keeps_brazil_residents_and_excludes_vr_from_rest_of_rj() -> None:
    codes = pd.Series(["330630", "330455", "355030", "invalid"])
    assert _geography(codes, "330630").tolist() == [
        "volta_redonda",
        "rest_of_rj_excluding_vr",
        "rest_of_brazil_excluding_rj",
        "outside_brazil",
    ]
