from vr_saude.discovery import select_resource


def test_resource_selection_prioritizes_parquet() -> None:
    resources = [
        {"name": "2020 CSV", "format": "CSV", "url": "https://example.test/2020.csv"},
        {"name": "2020 Parquet", "format": "", "url": "https://example.test/2020.parquet"},
    ]
    selected = select_resource(resources, 2020)
    assert selected["format"] == "PARQUET"
