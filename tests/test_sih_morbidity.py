from vr_saude.sih_morbidity import _parse_rows, _periods


def test_parse_rows_selects_named_tabnet_respiratory_categories() -> None:
    response = """
    <PRE>
    "10 Doen&ccedil;as do aparelho respirat&oacute;rio";117
    ".. Pneumonia";68
    ".. Bronquite aguda e bronquiolite aguda";2
    ".. Bronquite enfisema e outr doen&ccedil; pulm obstr cr&ocirc;n";9
    ".. Asma";2
    ".. Pneumoconiose";-
    "Total";1463
    </PRE>
    """
    rows, labels = _parse_rows(response)
    assert rows == {
        "resp_all": 117,
        "pneumonia": 68,
        "acute_bronchitis_bronchiolitis": 2,
        "copd": 9,
        "asthma": 2,
        "pneumoconiosis": 0,
    }
    assert labels["pneumonia"] == ".. Pneumonia"


def test_periods_are_contiguous_and_inclusive() -> None:
    assert _periods(2020, 11, 2021, 2) == [
        (2020, 11),
        (2020, 12),
        (2021, 1),
        (2021, 2),
    ]


def test_parse_rows_aggregates_named_cardiovascular_categories() -> None:
    response = """
    <PRE>
    "10 Doen&ccedil;as do aparelho respirat&oacute;rio";117
    "09 Doen&ccedil;as do aparelho circulat&oacute;rio";293
    ".. Hipertens&atilde;o essencial (prim&aacute;ria)";4
    ".. Outras doen&ccedil;as hipertensivas";3
    ".. Infarto agudo do mioc&aacute;rdio";49
    ".. Outras doen&ccedil;as isqu&ecirc;micas do cora&ccedil;&atilde;o";38
    ".. Insufici&ecirc;ncia card&iacute;aca";55
    ".. Hemorragia intracraniana";2
    ".. Infarto cerebral";1
    ".. Acid vascular cerebr n&atilde;o espec hemorr&aacute;g ou isq";5
    ".. Outras doen&ccedil;as cerebrovasculares";3
    </PRE>
    """
    rows, labels = _parse_rows(response)
    assert rows == {
        "resp_all": 117,
        "cardio_all": 293,
        "hypertension": 7,
        "ischemic_heart_disease": 87,
        "acute_myocardial_infarction": 49,
        "heart_failure": 55,
        "cerebrovascular": 11,
        "cardiorespiratory_all": 410,
    }
    assert labels["cerebrovascular"] == "Doenças cerebrovasculares"
