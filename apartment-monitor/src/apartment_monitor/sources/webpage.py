from __future__ import annotations

import httpx

from apartment_monitor.models import ApartmentListing, MonitorConfig, SourceConfig
from apartment_monitor.parsing import parse_apartment_html

from .base import Source


class WebPageSource(Source):
    def __init__(self, source: SourceConfig, config: MonitorConfig):
        super().__init__(source, config)

    def fetch(self) -> list[ApartmentListing]:
        html = _fetch_rendered(self.source) if self.source.render_js else _fetch_html(self.source)
        return parse_apartment_html(self.source, html)


def _fetch_html(source: SourceConfig) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
        ),
        **source.headers,
    }
    with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
        response = client.get(source.url)
        response.raise_for_status()
        return response.text


def _fetch_rendered(source: SourceConfig) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            f"{source.id} requires JavaScript rendering. Install with "
            "`pip install -e '.[browser]'` and run `playwright install chromium`."
        ) from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(extra_http_headers=source.headers or None)
        page.goto(source.url, wait_until="networkidle", timeout=60000)
        html = page.content()
        browser.close()
        return html
