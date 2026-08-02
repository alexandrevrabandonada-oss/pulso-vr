from vr_saude.age_sex_rates import AGE_GROUPS, SEXES, YEAR


def test_age_sex_rates_are_limited_to_census_year_and_official_sexes() -> None:
    assert YEAR == 2022
    assert SEXES == ["masculino", "feminino"]
    assert AGE_GROUPS == [
        "<1",
        "1-4",
        "5-14",
        "15-24",
        "25-44",
        "45-64",
        "65-74",
        "75+",
    ]
