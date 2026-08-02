import pandas as pd
import pytest

from vr_saude.age_sex import profile_counts


def test_profile_counts_calculates_within_outcome_share() -> None:
    counts = pd.DataFrame(
        [
            {
                "source_year": 2024,
                "geography": "volta_redonda",
                "outcome_id": "resp_all",
                "outcome_label": "respiratório",
                "age_group": "65-74",
                "sex": "masculino",
                "count": 3,
            },
            {
                "source_year": 2024,
                "geography": "volta_redonda",
                "outcome_id": "resp_all",
                "outcome_label": "respiratório",
                "age_group": "75+",
                "sex": "feminino",
                "count": 7,
            },
        ]
    )
    result = profile_counts(counts)
    assert result["total_count"].tolist() == [10, 10]
    assert result["share_pct"].tolist() == [pytest.approx(30.0), pytest.approx(70.0)]
