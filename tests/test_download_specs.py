from vr_saude.download import SAMPLE_SOURCES


def test_public_sample_sources_are_explicit_urls() -> None:
    assert SAMPLE_SOURCES
    for source_id, spec in SAMPLE_SOURCES.items():
        assert source_id
        assert spec["url"].startswith(("http://", "https://"))
        assert spec["filename"]
        assert spec["period"]
