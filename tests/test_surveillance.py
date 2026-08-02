import pytest

from vr_saude.surveillance import notification_rate_per_100k


def test_notification_rate_per_100k():
    assert notification_rate_per_100k(1_000, 1_000_000) == pytest.approx(100.0)


def test_notification_rate_rejects_invalid_population():
    with pytest.raises(ValueError):
        notification_rate_per_100k(1, 0)
