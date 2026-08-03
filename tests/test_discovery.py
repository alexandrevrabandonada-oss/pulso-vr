from vr_saude.discovery import select_resource


def test_resource_selection_prioritizes_parquet() -> None:
    resources = [
        {"name": "2020 CSV", "format": "CSV", "url": "https://example.test/2020.csv"},
        {"name": "2020 Parquet", "format": "", "url": "https://example.test/2020.parquet"},
    ]
    selected = select_resource(resources, 2020)
    assert selected["format"] == "PARQUET"


def test_resource_selection_does_not_confuse_update_date_with_data_year() -> None:
    resources = [
        {
            "name": "2019- Banco vivo 23/03/2026 - PARQUET",
            "format": "",
            "url": "https://example.test/SRAG/2019/INFLUD19-23-03-2026.parquet",
        },
        {
            "name": "2026- Banco vivo 27/07/2026 - PARQUET",
            "format": "",
            "url": "https://example.test/SRAG/2026/INFLUD26-27-07-2026.parquet",
        },
    ]
    selected = select_resource(resources, 2026)
    assert selected["url"].endswith("/2026/INFLUD26-27-07-2026.parquet")
