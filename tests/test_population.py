import json
from pathlib import Path

from vr_saude.population import _read_sidra_payload, requested_years


def test_empty_sidra_payload_is_explicitly_empty(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    path.write_text(json.dumps([{"D1C": "Município (Código)"}]), encoding="utf-8")
    assert _read_sidra_payload(path).empty


def test_requested_years_is_inclusive() -> None:
    assert requested_years(2020, 2022) == [2020, 2021, 2022]
