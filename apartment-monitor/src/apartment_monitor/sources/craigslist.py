from __future__ import annotations

import logging
from dataclasses import replace
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree

from bs4 import BeautifulSoup
import httpx

from apartment_monitor.models import ApartmentListing, MonitorConfig, SourceConfig
from apartment_monitor.parsing import parse_listing_text

from .base import Source

logger = logging.getLogger(__name__)
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
}


class CraigslistSource(Source):
    def __init__(self, source: SourceConfig, config: MonitorConfig):
        super().__init__(source, config)

    def fetch(self) -> list[ApartmentListing]:
        listings: list[ApartmentListing] = []
        for url in self.search_urls():
            try:
                listings.extend(_fetch_rss(self.source, url))
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 403:
                    logger.warning("Craigslist RSS returned 403; trying HTML fallback")
                    listings.extend(_fetch_html_with_warning(self.source, _rss_url_to_html_url(url)))
                else:
                    logger.warning("Craigslist RSS fetch failed: %s", exc)
            except Exception as exc:
                logger.warning("Craigslist RSS fetch failed: %s", exc)
        return _dedupe(listings)

    def search_urls(self) -> list[str]:
        urls = []
        query = " OR ".join(f'"{area}"' for area in self.config.neighborhoods)
        for criterion in self.config.criteria:
            params = {
                "format": "rss",
                "max_price": criterion.max_price,
                "min_bedrooms": criterion.bedrooms,
                "max_bedrooms": criterion.bedrooms,
                "min_bathrooms": int(criterion.min_bathrooms),
                "query": query,
                "sort": "date",
            }
            urls.append(f"{self.source.url}?{urlencode(params)}")
        return urls


def _fetch_rss(source: SourceConfig, url: str) -> list[ApartmentListing]:
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.get(url, headers=HEADERS)
        response.raise_for_status()
    return parse_craigslist_rss(source, response.text)


def _fetch_html_with_warning(source: SourceConfig, url: str) -> list[ApartmentListing]:
    try:
        return _fetch_html(source, url)
    except Exception as exc:
        logger.warning("Craigslist HTML fallback failed: %s", exc)
        return []


def _fetch_html(source: SourceConfig, url: str) -> list[ApartmentListing]:
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.get(url, headers=HEADERS)
        response.raise_for_status()
    return parse_craigslist_html(source, response.text)


def parse_craigslist_rss(source: SourceConfig, xml_text: str) -> list[ApartmentListing]:
    root = ElementTree.fromstring(xml_text)
    listings: list[ApartmentListing] = []
    for item in root.findall(".//item"):
        title = _text(item, "title")
        link = _text(item, "link") or source.url
        description = _text(item, "description")
        guid = _text(item, "guid")
        listing = parse_listing_text(source, title, link, description)
        if guid:
            listing = ApartmentListing(
                source_id=listing.source_id,
                source_name=listing.source_name,
                title=listing.title,
                url=listing.url,
                price=listing.price,
                bedrooms=listing.bedrooms,
                bathrooms=listing.bathrooms,
                neighborhood=listing.neighborhood,
                available_date=listing.available_date,
                address=listing.address,
                raw_text=listing.raw_text,
                external_id=guid,
            )
        listings.append(listing)
    return listings


def parse_craigslist_html(source: SourceConfig, html: str) -> list[ApartmentListing]:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("li.cl-static-search-result, .result-row, [data-pid]")
    listings: list[ApartmentListing] = []
    for row in rows:
        link = row.find("a", href=True)
        url = link["href"] if link else source.url
        title_el = row.select_one(".title, .result-title")
        price_el = row.select_one(".price, .result-price")
        hood_el = row.select_one(".location, .result-hood")
        title = title_el.get_text(" ", strip=True) if title_el else row.get_text(" ", strip=True)
        text = " ".join(
            part
            for part in [
                row.get_text(" ", strip=True),
                price_el.get_text(" ", strip=True) if price_el else "",
                hood_el.get_text(" ", strip=True) if hood_el else "",
            ]
            if part
        )
        listing = parse_listing_text(source, title, url, text)
        pid = row.get("data-pid")
        if pid:
            listing = replace(listing, external_id=f"craigslist-{pid}")
        if listing.price or listing.bedrooms or listing.bathrooms:
            listings.append(listing)
    return listings


def _text(item: ElementTree.Element, tag: str) -> str:
    child = item.find(tag)
    return child.text.strip() if child is not None and child.text else ""


def _rss_url_to_html_url(url: str) -> str:
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query) if key != "format"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _dedupe(listings: list[ApartmentListing]) -> list[ApartmentListing]:
    result: list[ApartmentListing] = []
    seen: set[str] = set()
    for listing in listings:
        key = listing.stable_id()
        if key in seen:
            continue
        seen.add(key)
        result.append(listing)
    return result
