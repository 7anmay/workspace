from __future__ import annotations

import json
import re
from hashlib import sha256
from html import unescape
from typing import Any

from bs4 import BeautifulSoup

from .models import ApartmentListing, SourceConfig

PRICE_RE = re.compile(r"\$\s*([1-9][0-9,]{2,})")
BED_RE = re.compile(r"\b([1-5])\s*(?:bed|beds|bd|bdrm|br|bedroom|bedrooms)\b", re.I)
BATH_RE = re.compile(r"\b([1-4](?:\.\d+)?)\s*(?:bath|baths|ba|bathroom|bathrooms)\b", re.I)
COMPACT_BED_BATH_RE = re.compile(r"\b([1-5])\s*b\s*/?\s*([1-4](?:\.\d+)?)\s*b\b", re.I)
UNIT_RE = re.compile(r"\b(?:apt|apartment|unit)\s*#?\s*([A-Za-z0-9-]+)\b", re.I)
DATE_RE = re.compile(r"\b(?:available|avail\.?|move[- ]?in)\s*:?\s*([A-Za-z]{3,9}\s+\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4}|now)\b", re.I)


def parse_apartment_html(source: SourceConfig, html: str) -> list[ApartmentListing]:
    soup = BeautifulSoup(html, "html.parser")
    for unwanted in soup(["script", "style", "noscript", "svg"]):
        unwanted.decompose()

    listings = _parse_json_ld(source, html)
    listings.extend(_parse_candidate_blocks(source, soup))
    if not listings:
        listings.extend(_parse_text_windows(source, soup.get_text(" ", strip=True)))
    return _dedupe(listings)


def parse_listing_text(source: SourceConfig, title: str, url: str, text: str) -> ApartmentListing:
    combined = _clean_text(f"{title} {text}")
    compact = COMPACT_BED_BATH_RE.search(combined)
    beds = int(compact.group(1)) if compact else _first_int(BED_RE, combined)
    baths = float(compact.group(2)) if compact else _first_float(BATH_RE, combined)
    price = _first_price(combined)
    unit_match = UNIT_RE.search(combined)
    date_match = DATE_RE.search(combined)
    listing_title = _clean_text(title) or _title_from_text(combined)
    if unit_match and unit_match.group(1) not in listing_title:
        listing_title = f"{listing_title} Unit {unit_match.group(1)}"
    return ApartmentListing(
        source_id=source.id,
        source_name=source.name,
        title=listing_title,
        url=url,
        price=price,
        bedrooms=beds,
        bathrooms=baths,
        neighborhood=source.neighborhood,
        available_date=date_match.group(1) if date_match else None,
        raw_text=combined,
        external_id=_listing_id(source.id, url, listing_title, price, beds, baths),
    )


def _parse_json_ld(source: SourceConfig, html: str) -> list[ApartmentListing]:
    soup = BeautifulSoup(html, "html.parser")
    listings: list[ApartmentListing] = []
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            payload = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        for item in _walk_json(payload):
            if not isinstance(item, dict):
                continue
            text = " ".join(str(item.get(key, "")) for key in ("name", "description", "address"))
            price = item.get("price") or item.get("lowPrice")
            if price:
                text = f"{text} ${price}"
            listing = parse_listing_text(
                source=source,
                title=str(item.get("name") or source.name),
                url=str(item.get("url") or source.url),
                text=text,
            )
            if listing.price or listing.bedrooms or listing.bathrooms:
                listings.append(listing)
    return listings


def _parse_candidate_blocks(source: SourceConfig, soup: BeautifulSoup) -> list[ApartmentListing]:
    selectors = [
        "[class*='unit' i]",
        "[class*='availability' i]",
        "[class*='floor' i]",
        "[class*='apartment' i]",
        "[id*='unit' i]",
        "[id*='availability' i]",
    ]
    blocks = []
    for selector in selectors:
        blocks.extend(soup.select(selector))

    listings: list[ApartmentListing] = []
    for block in blocks:
        text = _clean_text(block.get_text(" ", strip=True))
        if not _looks_like_listing(text):
            continue
        link = block.find("a", href=True)
        url = link["href"] if link else source.url
        if url.startswith("/"):
            url = _join_root(source.url, url)
        listings.append(parse_listing_text(source, _title_from_text(text), url, text))
    return listings


def _parse_text_windows(source: SourceConfig, text: str) -> list[ApartmentListing]:
    cleaned = _clean_text(text)
    listings: list[ApartmentListing] = []
    for price_match in PRICE_RE.finditer(cleaned):
        start = max(0, price_match.start() - 220)
        end = min(len(cleaned), price_match.end() + 260)
        window = cleaned[start:end]
        if _looks_like_listing(window):
            listings.append(parse_listing_text(source, _title_from_text(window), source.url, window))
    return listings


def _looks_like_listing(text: str) -> bool:
    if len(text) < 20:
        return False
    has_compact = COMPACT_BED_BATH_RE.search(text)
    has_words = BED_RE.search(text) and BATH_RE.search(text)
    return bool(PRICE_RE.search(text) and (has_compact or has_words))


def _walk_json(payload: Any) -> list[Any]:
    if isinstance(payload, dict):
        items = [payload]
        for value in payload.values():
            items.extend(_walk_json(value))
        return items
    if isinstance(payload, list):
        items = []
        for value in payload:
            items.extend(_walk_json(value))
        return items
    return []


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


def _first_price(text: str) -> int | None:
    match = PRICE_RE.search(text)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def _first_int(pattern: re.Pattern[str], text: str) -> int | None:
    match = pattern.search(text)
    return int(match.group(1)) if match else None


def _first_float(pattern: re.Pattern[str], text: str) -> float | None:
    match = pattern.search(text)
    return float(match.group(1)) if match else None


def _title_from_text(text: str) -> str:
    trimmed = _clean_text(text)
    if len(trimmed) <= 90:
        return trimmed
    return f"{trimmed[:87].rstrip()}..."


def _clean_text(text: str) -> str:
    return " ".join(unescape(text).split())


def _join_root(base_url: str, path: str) -> str:
    parts = base_url.split("/", 3)
    if len(parts) < 3:
        return path
    return f"{parts[0]}//{parts[2]}{path}"


def _listing_id(
    source_id: str,
    url: str,
    title: str,
    price: int | None,
    beds: int | None,
    baths: float | None,
) -> str:
    key = f"{source_id}|{url}|{title}|{price}|{beds}|{baths}"
    return sha256(key.encode("utf-8")).hexdigest()[:24]
