"""Safe Phase 4 preview and preference API tests."""
from types import SimpleNamespace
import pytest
from app.web.operator import preview, Preview, preferences, save_preferences, Preferences


class DB:
    def __init__(self):
        self.values = {}

    def get_setting(self, key, default=None):
        return self.values.get(key, default)

    def set_setting(self, key, value):
        self.values[key] = value


@pytest.mark.asyncio
async def test_preview_never_transmits_and_respects_payload_limit():
    result = await preview(Preview(message="🌪" * 1000))
    assert result["transmitted"] is False
    assert result["truncated"] is True
    assert len(result["preview"].encode("utf-8")) <= result["limit"]


@pytest.mark.asyncio
async def test_preferences_round_trip():
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=DB())))
    await save_preferences(request, Preferences(compact=True, advanced=True, monitor=False))
    result = await preferences(request)
    assert result == {"compact": True, "advanced": True, "monitor": False, "show_radios": True, "show_activity": True, "show_weather": True, "show_map": True}


def test_operator_notifications():
    from app.web.operator import build_notifications
    alerts = build_notifications([{"enabled": True, "connected": False}], "error timeout", 6)
    assert any(a["level"] == "critical" for a in alerts)
    assert any("polling" in a["message"].lower() for a in alerts)
    assert any("queue" in a["message"].lower() for a in alerts)


def test_operator_notifications_healthy():
    from app.web.operator import build_notifications
    assert build_notifications([{"enabled": True, "connected": True}], "ok", 0) == []
