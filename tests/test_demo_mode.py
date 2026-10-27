"""Offline demonstration page contract checks."""
from pathlib import Path

from app.web.operator import demonstration


def test_demo_route_has_no_hardware_dependencies():
    import asyncio
    response = asyncio.run(demonstration())
    text = response.body.decode("utf-8")
    assert "DEMONSTRATION" in text
    assert "No radio transmissions" in text
    assert "No live weather API calls" in text
    assert "Severe weather" in text
    assert "Radio outage" in text


def test_screenshot_script_uses_static_demo_file():
    script = Path("scripts/capture_demo_screenshots.py").read_text(encoding="utf-8")
    assert "DEMO.as_uri()" in script
    assert "normal" in script and "storm" in script and "offline" in script
