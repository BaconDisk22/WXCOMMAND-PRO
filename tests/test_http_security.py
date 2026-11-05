"""HTTP management boundary regression tests; no radio transmissions."""
from fastapi.testclient import TestClient
from app.main import create_app


def test_cross_origin_write_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("MESH_WX_HOST", "127.0.0.1")
    monkeypatch.setenv("MESH_WX_DB", str(tmp_path / "test.db"))
    client = TestClient(create_app())
    response = client.post("/api/ux/preferences", json={}, headers={
        "host": "127.0.0.1:8000", "origin": "https://attacker.example"
    })
    assert response.status_code == 403


def test_cross_site_fetch_metadata_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("MESH_WX_HOST", "127.0.0.1")
    monkeypatch.setenv("MESH_WX_DB", str(tmp_path / "test.db"))
    client = TestClient(create_app())
    response = client.post("/api/ux/preferences", json={}, headers={"sec-fetch-site": "cross-site"})
    assert response.status_code == 403


def test_remote_binding_without_token_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("MESH_WX_HOST", "0.0.0.0")
    monkeypatch.delenv("WXCOMMAND_API_TOKEN", raising=False)
    monkeypatch.setenv("MESH_WX_DB", str(tmp_path / "test.db"))
    response = TestClient(create_app()).get("/operator")
    assert response.status_code == 503


def test_remote_binding_rejects_missing_token(monkeypatch, tmp_path):
    monkeypatch.setenv("MESH_WX_HOST", "0.0.0.0")
    monkeypatch.setenv("WXCOMMAND_API_TOKEN", "long-secret-value")
    monkeypatch.setenv("MESH_WX_DB", str(tmp_path / "test.db"))
    response = TestClient(create_app()).get("/operator")
    assert response.status_code == 401


def test_remote_binding_accepts_valid_token(monkeypatch, tmp_path):
    monkeypatch.setenv("MESH_WX_HOST", "0.0.0.0")
    monkeypatch.setenv("WXCOMMAND_API_TOKEN", "long-secret-value")
    monkeypatch.setenv("MESH_WX_DB", str(tmp_path / "test.db"))
    response = TestClient(create_app()).get("/operator", headers={"x-wxcommand-token": "long-secret-value"})
    assert response.status_code == 200
