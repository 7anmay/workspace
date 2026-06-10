from __future__ import annotations

from urllib.parse import urlencode
from xml.etree import ElementTree

import httpx

from apartment_monitor.models import ApartmentListing, MonitorConfig, SourceConfig
from apartment_monitor.parsing import parse_listing_text

from .base import Source


class CraigslistSource(Source):
    def __init__(self, source: SourceConfig, config: MonitorConfig):
        super().__init__(source, config)

    def fetch(self) -> list[ApartmentListing]:
        listings: list[ApartmentListing] = []
        for url in self.search_urls():
            listings.extend(_fetch_rss(self.source, url))
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
        response = client.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
                )
            },
        )
        response.raise_for_status()
    return parse_craigslist_rss(source, response.text)


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


def _text(item: ElementTree.Element, tag: str) -> str:
    child = item.find(tag)
    return child.text.strip() if child is not None and child.text else ""


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
