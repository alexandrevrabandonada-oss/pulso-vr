import pandas as pd

from vr_saude.municipal_profiles import apply_profile_applicability, complementary_suppression


def test_complementary_suppression_protects_lone_small_cell() -> None:
    frame = pd.DataFrame([
        {"outcome_id": "lung", "age_group": "65-74", "sex": "feminino", "municipality_code_ibge": "3300100", "count": 3},
        {"outcome_id": "lung", "age_group": "65-74", "sex": "feminino", "municipality_code_ibge": "3300209", "count": 5},
        {"outcome_id": "lung", "age_group": "65-74", "sex": "feminino", "municipality_code_ibge": "3300308", "count": 8},
    ])

    protected = complementary_suppression(frame)

    assert protected.loc[protected["municipality_code_ibge"].eq("3300100"), "suppression_status"].item() == "suppressed"
    assert protected.loc[protected["municipality_code_ibge"].eq("3300209"), "suppression_status"].item() == "suppressed_complementary"
    assert protected.loc[protected["municipality_code_ibge"].eq("3300308"), "suppression_status"].item() == "published"


def test_complementary_suppression_does_not_add_noise_when_multiple_cells_are_small() -> None:
    frame = pd.DataFrame([
        {"outcome_id": "lung", "age_group": "65-74", "sex": "masculino", "municipality_code_ibge": "3300100", "count": 0},
        {"outcome_id": "lung", "age_group": "65-74", "sex": "masculino", "municipality_code_ibge": "3300209", "count": 4},
        {"outcome_id": "lung", "age_group": "65-74", "sex": "masculino", "municipality_code_ibge": "3300308", "count": 8},
    ])

    protected = complementary_suppression(frame)

    assert protected["suppression_status"].tolist() == ["suppressed", "suppressed", "published"]


def test_sex_specific_profiles_mark_non_applicable_cells() -> None:
    frame = pd.DataFrame([
        {"outcome_id": "cervix", "sex": "masculino", "suppression_status": "suppressed"},
        {"outcome_id": "cervix", "sex": "feminino", "suppression_status": "published"},
        {"outcome_id": "prostate", "sex": "feminino", "suppression_status": "suppressed"},
    ])
    result = apply_profile_applicability(frame)
    assert result["suppression_status"].tolist() == ["not_applicable", "published", "not_applicable"]
