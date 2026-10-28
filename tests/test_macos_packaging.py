"""Desktop binding fails closed instead of opening an unrelated local service."""
import socket
import pytest
from app.macos_desktop import reserve_socket


def test_desktop_reserves_loopback_before_startup():
    sock = reserve_socket('127.0.0.1', 0)
    try:
        host, port = sock.getsockname()
        assert host == '127.0.0.1'
        with socket.create_connection((host, port), timeout=1):
            pass
        with pytest.raises(OSError):
            reserve_socket(host, port)
    finally:
        sock.close()
    replacement = reserve_socket(host, port)
    replacement.close()


def test_build_refuses_non_macos(monkeypatch, tmp_path):
    from deploy import build_macos_app
    monkeypatch.setattr(build_macos_app.sys, 'platform', 'linux')
    with pytest.raises(RuntimeError, match='Intel macOS'):
        build_macos_app.build(tmp_path)
    assert not list(tmp_path.iterdir())
