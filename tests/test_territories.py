from pathlib import Path

from vr_saude.config import load_config


def test_primary_comparator_excludes_selected_municipality_from_aggregates() -> None:
    root = Path(__file__).resolve().parents[1]
    territories = load_config("territories.yml", root)
    rule = territories["comparators"]["primary"]["rule"].lower()
    assert "selected municipality" in rule
    assert "numerator" in rule
    assert "denominator" in rule
