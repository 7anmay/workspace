from __future__ import annotations

import logging

import httpx

from apartment_monitor.models import ApartmentListing, MonitorConfig, SourceConfig
from apartment_monitor.parsing import parse_apartment_html

from .base import Source

logger = logging.getLogger(__name__)
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
}


class WebPageSource(Source):
    def __init__(self, source: SourceConfig, config: MonitorConfig):
        super().__init__(source, config)

    def fetch(self) -> list[ApartmentListing]:
        html = _fetch_rendered(self.source) if self.source.render_js else _fetch_html(self.source)
        return parse_apartment_html(self.source, html)


def _fetch_html(source: SourceConfig) -> str:
    headers = {
        **DEFAULT_HEADERS,
        **source.headers,
    }
    with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
        response = client.get(source.url)
        response.raise_for_status()
        return response.text


def _fetch_rendered(source: SourceConfig) -> str:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            f"{source.id} requires JavaScript rendering. Install with "
            "`pip install -e '.[browser]'` and run `playwright install chromium`."
        ) from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        page = browser.new_page(
            extra_http_headers=source.headers or None,
            user_agent=DEFAULT_HEADERS["User-Agent"],
            viewport={"width": 1365, "height": 900},
        )
        page.set_default_timeout(30000)
        _block_heavy_assets(page)
        try:
            return _capture_rendered_html(page, source, (PlaywrightTimeoutError,))
        finally:
            browser.close()


def _capture_rendered_html(page, source: SourceConfig, timeout_error_types: tuple[type[BaseException], ...]) -> str:
    try:
        page.goto(source.url, wait_until="domcontentloaded", timeout=30000)
    except timeout_error_types:
        logger.warning("%s page load timed out; parsing partial HTML", source.id)

    try:
        page.wait_for_load_state("load", timeout=10000)
    except timeout_error_types:
        logger.info("%s did not reach full load state before parsing", source.id)

    page.wait_for_timeout(3000)
    html = page.content()
    if not html.strip():
        raise RuntimeError(f"{source.id} returned empty rendered HTML")
    return html


def _block_heavy_assets(page) -> None:
    def route_handler(route):
        if route.request.resource_type in {"font", "image", "media"}:
            route.abort()
        else:
            route.continue_()

    try:
        page.route("**/*", route_handler)
    except Exception:
        logger.debug("Unable to install browser route handler", exc_info=True)
