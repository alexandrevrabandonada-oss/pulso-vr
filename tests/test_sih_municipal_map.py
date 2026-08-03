from vr_saude.sih_municipal_map import _parse_municipal_rows


def test_parse_municipal_rows_requires_all_rj_municipalities() -> None:
    lines = ['"Município";"Internações"']
    lines.extend(f'"330{i:03d} MUNICIPIO {i}";{i}' for i in range(1, 93))
    payload = ("<PRE>\n" + "\n".join(lines) + "\n</PRE>").encode("latin1")
    rows = _parse_municipal_rows(payload)
    assert len(rows) == 92
    assert rows["330001"] == 1
