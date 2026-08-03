import json
from pathlib import Path

from vr_saude.raw_validation import validate_raw_file
from vr_saude.provenance import sha256_file, write_sha256_sidecar


def test_geojson_feature_collection_is_validated(tmp_path: Path) -> None:
    target = tmp_path / "municipios.geojson"
    target.write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
    write_sha256_sidecar(target, sha256_file(target))
    result = validate_raw_file(target)
    assert result["ok"] is True
    assert result["format_details"]["features"] == 0


def test_painel_oncologia_two_column_csv_is_validated(tmp_path: Path) -> None:
    target = tmp_path / "painel_oncologia.csv"
    target.write_text('"Ano do diagnóstico";"Casos"\n"2024";"10"\n', encoding="latin1")
    write_sha256_sidecar(target, sha256_file(target))
    result = validate_raw_file(target)
    assert result["ok"] is True
    assert result["format_details"]["source_layout"] == "Painel-Oncologia TabNet two-column result"
