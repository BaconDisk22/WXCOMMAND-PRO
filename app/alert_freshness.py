"""Guard against broadcasting alerts whose NWS expiry has passed."""
from datetime import datetime, timezone


def alert_is_expired(expires: str, now: datetime | None = None) -> bool:
    """Treat missing/malformed dates as unknown rather than silently drop alerts.

    NWS timestamps are ISO 8601. An expiry exactly equal to now is expired.
    """
    if not expires:
        return False
    try:
        expiry = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        if expiry.tzinfo is None:
            return False
        current = now or datetime.now(timezone.utc)
        return expiry <= current.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return False
