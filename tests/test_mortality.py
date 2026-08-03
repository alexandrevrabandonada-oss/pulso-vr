from pathlib import Path

from vr_saude.mortality import period_status


ROOT = Path(__file__).resolve().parents[1]


def test_period_status_marks_cancer_care_disruption() -> None:
    assert period_status(ROOT, 2020, "all_malignant_neoplasms") == "cancer_care_disruption"


def test_period_status_marks_respiratory_pandemic() -> None:
    assert period_status(ROOT, 2020, "resp_all") == "respiratory_pandemic"


def test_period_status_marks_cardiorespiratory_pandemic_context() -> None:
    assert period_status(ROOT, 2020, "cardiorespiratory_all") == "cardiorespiratory_pandemic_context"
