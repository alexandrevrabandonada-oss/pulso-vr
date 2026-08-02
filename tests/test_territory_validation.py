from vr_saude.territory_validation import _code


def test_code_normalization_keeps_datasus_code_without_leading_zeroes():
    assert _code("330630") == "330630"
    assert _code(330630) == "330630"
    assert _code(None) == ""
