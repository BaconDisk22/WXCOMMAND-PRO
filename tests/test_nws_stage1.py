"""NWS client error handling regression tests (offline; no radio traffic)."""
import httpx
import pytest

from app.nws import NWSClient, NWSError


@pytest.mark.asyncio
async def test_nws_active_alert_fetch_sends_contact_and_zone(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, **kwargs):
            calls.append(("init", kwargs))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, **kwargs):
            calls.append(("get", url, kwargs))
            return httpx.Response(200, json={"features": []}, headers={"date": "Tue, 13 Oct 2026 20:00:00 GMT"})

    monkeypatch.setattr("app.nws.httpx.AsyncClient", FakeClient)
    client = NWSClient("ops@example.org", timeout=3)
    result, raw = await client.fetch_active("NCZ053", max_retries=1)
    assert result == {"features": []}
    assert '"features"' in raw
    assert calls[1][2]["params"] == {"zone": "NCZ053"}
    assert "ops@example.org" in calls[1][2]["headers"]["User-Agent"]
    assert client.last_server_date == "Tue, 13 Oct 2026 20:00:00 GMT"


@pytest.mark.asyncio
async def test_nws_rejects_nonretryable_error(monkeypatch):
    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, **kwargs):
            return httpx.Response(403, text="Access denied")

    monkeypatch.setattr("app.nws.httpx.AsyncClient", FakeClient)
    with pytest.raises(NWSError, match="HTTP 403"):
        await NWSClient("ops@example.org").fetch_active("NCZ053", max_retries=3)
