from pathlib import Path

from vr_saude.config import load_config


def test_primary_comparator_excludes_volta_redonda() -> None:
    root = Path(__file__).resolve().parents[1]
    territories = load_config("territories.yml", root)
    rule = territories["comparators"]["primary"]["rule"].lower()
    assert "3306305" in rule
    assert "except" in rule
