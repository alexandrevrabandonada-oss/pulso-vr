from pathlib import Path

from vr_saude.sih_tabnet import SihQueryResult, write_harmonized_series


def _result(year: int, month: int, value: int) -> SihQueryResult:
    return SihQueryResult(
        year=year,
        month=month,
        archive=f"nrrj{year % 100:02d}{month:02d}.dbf",
        municipality_value="93",
        municipality_code="330630",
        municipality_name="Volta Redonda",
        hospitalizations=value,
        response=b"",
    )


def test_harmonized_series_keeps_one_row_per_period(tmp_path: Path) -> None:
    root = tmp_path
    (root / "config").mkdir()
    (root / "config" / "territories.yml").write_text(
        "volta_redonda:\n  datasus_code_6_expected: '330630'\n  ibge_code_7: '3306305'\n",
        encoding="utf-8",
    )
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    for month in (1, 2):
        path = raw / f"sih_tabnet_nrrj_2024_{month:02d}.html"
        path.write_text(
            '<TITLE>TabNet Win32</TITLE>"Total" Sistema de Informações Hospitalares',
            encoding="latin1",
        )
    (root / "data" / "interim").mkdir()
    interim, report = write_harmonized_series(root, [_result(2024, 2, 11), _result(2024, 1, 10)])
    assert interim.read_text(encoding="utf-8").count("2024-") == 2
    assert '"rows": 2' in report.read_text(encoding="utf-8")
