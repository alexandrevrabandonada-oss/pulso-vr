from pathlib import Path

from vr_saude.layout_validation import validate_known_layouts


def test_known_raw_layouts_pass() -> None:
    root = Path(__file__).resolve().parents[1]
    results = validate_known_layouts(root)
    assert results
    assert all(item["ok"] for item in results)
