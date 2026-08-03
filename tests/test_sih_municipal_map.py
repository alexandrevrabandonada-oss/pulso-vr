from pathlib import Path

import pytest

from vr_saude.sih_municipal_map import _parse_municipal_rows, build_sih_municipal_map


def test_parse_municipal_rows_requires_all_rj_municipalities() -> None:
    lines = ['"Município";"Internações"']
    lines.extend(f'"330{i:03d} MUNICIPIO {i}";{i}' for i in range(1, 93))
    payload = ("<PRE>\n" + "\n".join(lines) + "\n</PRE>").encode("latin1")
    rows = _parse_municipal_rows(payload)
    assert len(rows) == 92
    assert rows["330001"] == 1


def test_selective_outcome_validation_rejects_unknown_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown SIH municipal outcomes"):
        build_sih_municipal_map(tmp_path, outcome_ids=["not_configured"])
