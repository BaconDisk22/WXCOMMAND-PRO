"""NWS expiry checks run offline with a fixed clock."""
from datetime import datetime, timezone

from app.alert_freshness import alert_is_expired

NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)


def test_expired_utc_alert_is_rejected():
    assert alert_is_expired("2026-10-14T11:59:59Z", NOW)


def test_expiry_at_current_instant_is_expired():
    assert alert_is_expired("2026-10-14T12:00:00+00:00", NOW)


def test_future_alert_is_kept():
    assert not alert_is_expired("2026-10-14T12:00:01Z", NOW)


def test_offset_timezone_is_respected():
    assert alert_is_expired("2026-10-14T08:00:00-04:00", NOW)
    assert not alert_is_expired("2026-10-14T09:00:00-04:00", NOW)


def test_missing_or_malformed_expiry_does_not_drop_alert():
    assert not alert_is_expired("", NOW)
    assert not alert_is_expired("not-a-date", NOW)
    assert not alert_is_expired("2026-10-14T10:00:00", NOW)
