"""Capture deterministic screenshots of the offline WXCOMMAND-PRO demonstration.

Requires: pip install playwright && python -m playwright install chromium
No app server, live NWS requests, or connected radio hardware is needed.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "app" / "web" / "templates" / "demo.html"
OUTPUT = ROOT / "dist" / "screenshots"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        for scenario in ("normal", "storm", "offline"):
            page.goto(DEMO.as_uri() + "?scenario=" + scenario, wait_until="load")
            page.locator("#scenario").wait_for()
            assert page.locator("#scenario").input_value() == scenario
            assert page.get_by_text("DEMONSTRATION", exact=False).count() > 0
            page.screenshot(path=str(OUTPUT / ("wxcommand-pro-" + scenario + ".png")), full_page=True)
        browser.close()


if __name__ == "__main__":
    main()
