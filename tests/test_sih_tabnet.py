from vr_saude.sih_tabnet import _archive_value, _definition_municipality_value, _parse_hospitalizations


DEFINITION = """
<OPTION VALUE="93">330630 VOLTA REDONDA
<OPTION VALUE="nrrj2401.dbf">Jan/2024
"""


def test_tabnet_definition_parsing():
    assert _definition_municipality_value(DEFINITION, "330630") == "93"
    assert _archive_value(DEFINITION, 2024, 1) == "nrrj2401.dbf"


def test_tabnet_result_parsing():
    response = '"330630 VOLTA REDONDA";1.463\n"Total";1.463'
    assert _parse_hospitalizations(response, "330630") == 1463
