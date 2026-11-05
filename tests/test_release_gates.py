"""Release-gate tests: safe defaults, API validation and non-transmitting preview."""
import pytest
from fastapi import HTTPException
from app.config import load_bootstrap
from app.web.operator import Preview, weather_map


def test_http_default_is_loopback(monkeypatch, tmp_path):
    monkeypatch.delenv("MESH_WX_HOST", raising=False)
    monkeypatch.setenv("MESH_WX_DB", str(tmp_path / "mesh.db"))
    assert load_bootstrap().http_host == "127.0.0.1"


@pytest.mark.asyncio
async def test_preview_rejects_empty_payload():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Preview(message="")


@pytest.mark.asyncio
async def test_weather_map_handles_unavailable_upstream(monkeypatch):
    import httpx

    async def fail(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx.AsyncClient, "get", fail)
    with pytest.raises(HTTPException) as exc:
        await weather_map()
    assert exc.value.status_code == 503
