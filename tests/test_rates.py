from vr_saude.rates import _rate_ratio_interval, poisson_count_interval


def test_poisson_interval_zero_count_has_zero_lower_bound() -> None:
    lower, upper = poisson_count_interval(0)
    assert lower == 0
    assert upper > 0


def test_poisson_interval_is_ordered_for_positive_count() -> None:
    lower, upper = poisson_count_interval(25)
    assert 0 < lower < 25 < upper


def test_rate_ratio_interval_uses_population_denominators() -> None:
    lower, upper = _rate_ratio_interval(60, 2871, 279898, 16939781)
    assert lower is not None and upper is not None
    assert lower < 1.2648 < upper
