from __future__ import annotations

import os

from slack_sdk import WebClient

from .filtering import matching_criterion
from .models import ApartmentListing, MonitorConfig


class SlackNotifier:
    def __init__(self, token: str | None = None, channel_id: str | None = None):
        self.token = token or os.getenv("SLACK_BOT_TOKEN")
        self.channel_id = channel_id or os.getenv("SLACK_CHANNEL_ID")
        self.client = WebClient(token=self.token) if self.token else None

    def enabled(self) -> bool:
        return bool(self.client and self.channel_id)

    def send_listings(self, listings: list[ApartmentListing], config: MonitorConfig) -> None:
        if not self.enabled() or not listings:
            return
        message = format_listing_batch(listings, config)
        self.client.chat_postMessage(channel=self.channel_id, text=message)

    def send_text(self, text: str) -> None:
        if not self.enabled():
            return
        self.client.chat_postMessage(channel=self.channel_id, text=text)


def format_listing_batch(listings: list[ApartmentListing], config: MonitorConfig) -> str:
    lines = [f":house_with_garden: {len(listings)} new apartment match(es)"]
    for listing in listings:
        criterion = matching_criterion(listing, config.criteria, config.neighborhoods)
        label = criterion.label if criterion and criterion.label else "matching criteria"
        details = []
        if listing.price:
            details.append(f"${listing.price:,}")
        if listing.bedrooms is not None and listing.bathrooms is not None:
            details.append(f"{listing.bedrooms}B/{listing.bathrooms:g}B")
        if listing.neighborhood:
            details.append(listing.neighborhood)
        if listing.available_date:
            details.append(f"available {listing.available_date}")
        summary = " · ".join(details)
        lines.append(f"• <{listing.url}|{listing.title}> — {summary} ({label}, {listing.source_name})")
    return "\n".join(lines)
