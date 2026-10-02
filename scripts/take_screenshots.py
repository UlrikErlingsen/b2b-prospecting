"""Capture README screenshots of a running Prospect Signal (maintainers only; uses fictional demo data).

    python -m pip install playwright      # dev-only; uses your installed Edge or Chrome, downloads no browser
    python -m streamlit run app.py --server.port 8589
    python scripts/take_screenshots.py [--channel msedge|chrome] [--base http://127.0.0.1:8589]

Seed the demo shortlist first if you want the shortlist and export shots to show rows.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
# name -> (url path, CSS selector to scroll to first, or None)
SHOTS = {
    "welcome": ("", None),
    "icp-filters": ("icp", None),
    "icp-results": ("icp", '[data-testid="stMetric"]'),
    "market-size": ("market", ".js-plotly-plot"),
    "shortlist": ("shortlist", None),
    "export": ("export", None),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8589")
    parser.add_argument("--channel", default="msedge")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.channel, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        for name, (path, scroll_to) in SHOTS.items():
            page.goto(f"{args.base}/{path}?dataset=demo")
            page.wait_for_selector(".sg-mast", timeout=60_000)
            page.wait_for_selector('[data-testid="stStatusWidget"]', state="detached", timeout=60_000)
            if scroll_to:
                page.locator(scroll_to).first.scroll_into_view_if_needed()
                page.mouse.wheel(0, -80)
            page.wait_for_timeout(2500)  # charts and data grids finish drawing
            out = ROOT / "assets" / f"screenshot-{name}.png"
            page.screenshot(path=str(out), full_page=False)
            print(f"wrote {out}")
        browser.close()


if __name__ == "__main__":
    main()
