"""Operator workflow tests for safe notification handling."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.web.operator import NotificationAck, acknowledge_notification, notification_history


class DB:
    def __init__(self):
        self.data = {}
    def get_setting(self, key, default=None):
        return self.data.get(key, default)
    def set_setting(self, key, value):
        self.data[key] = value


def make_request():
    tx = SimpleNamespace(status=lambda: [{"enabled": True, "connected": False}], queue_depth=0)
    poller = SimpleNamespace(status=SimpleNamespace(last_poll_result="ok"))
    db = DB()
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(tx=tx, poller=poller, db=db)))


@pytest.mark.asyncio
async def test_acknowledgement_persists():
    request = make_request()
    current = await notification_history(request)
    key = current["notifications"][0]["id"]
    assert (await acknowledge_notification(request, NotificationAck(id=key)))["acknowledged"] == key
    assert (await notification_history(request))["notifications"][0]["acknowledged_at"]


@pytest.mark.asyncio
async def test_cannot_acknowledge_unknown_notification():
    request = make_request()
    with pytest.raises(HTTPException) as exc:
        await acknowledge_notification(request, NotificationAck(id="not-real"))
    assert exc.value.status_code == 404
