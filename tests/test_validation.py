from pathlib import Path

from vr_saude.validate import validate_project


def test_project_validation_passes() -> None:
    assert validate_project(Path(__file__).resolve().parents[1]) == []
