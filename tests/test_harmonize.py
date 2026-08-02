from pathlib import Path
from zipfile import ZipFile

import pyarrow.parquet as pq

from vr_saude.harmonize import harmonize_file


def test_harmonize_sim_uses_named_fields_and_keeps_residence_separate(tmp_path: Path) -> None:
    root = tmp_path
    (root / "config").mkdir()
    (root / "config" / "territories.yml").write_text(
        "volta_redonda:\n  datasus_code_6_expected: '330630'\n  ibge_code_7: '3306305'\n",
        encoding="utf-8",
    )
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    csv_text = (
        "CAUSABAS;IDADE;SEXO;CODMUNOCOR;CODMUNRES;DTOBITO;DTNASC\n"
        "U071;465;1;330455;330630;06082010;09041945\n"
    )
    archive_path = raw / "sim_2010_test.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("Mortalidade_Geral_2010.csv", csv_text.encode("latin1"))
    result = harmonize_file(root, archive_path, chunk_size=10)
    table = pq.read_table(root / result["output_path"])
    assert result["rows"] == 1
    assert result["residence_vr_rows"] == 1
    assert table.column("municipality_code_datasus").to_pylist() == ["330630"]
    assert table.column("municipality_code_occurrence").to_pylist() == ["330455"]
