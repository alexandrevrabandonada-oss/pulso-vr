import pandas as pd

from vr_saude.interrupted_respiratory import _add_interruption_variables


def test_interruption_variables_mark_march_2020_without_shift_at_break() -> None:
    frame = pd.DataFrame(
        {
            "period": pd.to_datetime(["2020-02-01", "2020-03-01", "2020-04-01"]),
            "year": [2020, 2020, 2020],
            "population": [1000, 1000, 1000],
        }
    )
    result = _add_interruption_variables(frame)
    assert result["pandemic_step"].tolist() == [0, 1, 1]
    assert result["post_pandemic_time"].tolist() == [0, 0, 1]
    assert result["monthly_population"].tolist() == [1000 / 12] * 3
