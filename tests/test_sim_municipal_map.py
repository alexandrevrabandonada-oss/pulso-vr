from pathlib import Path

import pandas as pd

from vr_saude.sim_municipal_map import _counts


def test_counts_reads_parameterized_harmonized_year(tmp_path: Path) -> None:
    interim = tmp_path / "data" / "interim"
    raw = tmp_path / "data" / "raw"
    interim.mkdir(parents=True)
    raw.mkdir(parents=True)
    source = raw / "sim_2024.zip"
    source.write_bytes(b"source")
    pd.DataFrame([
        {"source_file": "data/raw/sim_2024.zip", "municipality_code_datasus": "330330", "residence_code_valid": True, "underlying_cause": "C349"},
        {"source_file": "data/raw/sim_2024.zip", "municipality_code_datasus": "330330", "residence_code_valid": True, "underlying_cause": "C349"},
        {"source_file": "data/raw/sim_2024.zip", "municipality_code_datasus": "355030", "residence_code_valid": True, "underlying_cause": "C349"},
    ]).to_parquet(interim / "sim_2024_harmonized.parquet", index=False)

    counts, raw_path, harmonized_path = _counts(
        tmp_path,
        [{"id": "lung", "code_ranges": ["C33-C34"]}],
        2024,
    )

    assert counts.to_dict("records") == [{"municipality_code_datasus": "330330", "outcome_id": "lung", "count": 2}]
    assert raw_path == source
    assert harmonized_path == interim / "sim_2024_harmonized.parquet"
