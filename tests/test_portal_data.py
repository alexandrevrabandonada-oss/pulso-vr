from vr_saude.portal_data import _topology_geometry, suppress_public_observation


def test_publication_suppresses_small_cells_before_frontend() -> None:
    observation = {
        "value": 1.4,
        "count": 4,
        "ciLow": 0.4,
        "ciHigh": 3.0,
        "denominator": 100_000,
    }
    published = suppress_public_observation(observation)
    assert published["suppressed"] is True
    assert published["suppressionReason"] == "small_cell_lt_5"
    assert published["value"] is None
    assert published["count"] is None
    assert published["ciLow"] is None
    assert published["ciHigh"] is None
    assert published["denominator"] == 100_000


def test_publication_keeps_non_small_cell_values() -> None:
    observation = {"value": 2.0, "count": 5, "ciLow": 1.0, "ciHigh": 3.0}
    published = suppress_public_observation(observation)
    assert published["suppressed"] is False
    assert published["count"] == 5


def test_topology_conversion_keeps_polygon_as_arc_reference() -> None:
    arcs: list[object] = []
    converted = _topology_geometry(
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        arcs,
    )
    assert converted == {"type": "Polygon", "arcs": [[0]]}
    assert arcs == [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]]]
