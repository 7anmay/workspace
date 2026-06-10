from __future__ import annotations

import logging
import time
from pathlib import Path

from .config import ConfigStore
from .filtering import listing_matches
from .models import ApartmentListing, MonitorConfig, SourceConfig
from .notifier import SlackNotifier
from .sources import CraigslistSource, Source, WebPageSource
from .state import StateStore

logger = logging.getLogger(__name__)


class ApartmentMonitor:
    def __init__(
        self,
        config_store: ConfigStore,
        notifier: SlackNotifier | None = None,
        notify: bool = True,
    ):
        self.config_store = config_store
        self.notifier = notifier
        self.notify = notify

    def run_once(self) -> list[ApartmentListing]:
        config = self.config_store.load()
        state_path = _resolve_state_path(self.config_store.path, config.state_path)
        state = StateStore(state_path)
        seen = state.load_seen()
        matches = self._fetch_matches(config)
        fresh = [listing for listing in matches if listing.stable_id() not in seen]
        seen.update(listing.stable_id() for listing in matches)
        state.save_seen(seen)
        if self.notify and self.notifier:
            if config.slack_channel_id:
                self.notifier.channel_id = config.slack_channel_id
            self.notifier.send_listings(fresh, config)
        return fresh

    def watch(self) -> None:
        while True:
            try:
                fresh = self.run_once()
                logger.info("Apartment search complete: %s new match(es)", len(fresh))
            except Exception:
                logger.exception("Apartment search failed")
            config = self.config_store.load()
            time.sleep(max(1, config.interval_minutes) * 60)

    def _fetch_matches(self, config: MonitorConfig) -> list[ApartmentListing]:
        results: list[ApartmentListing] = []
        for source_config in config.sources:
            if not source_config.enabled:
                continue
            source = build_source(source_config, config)
            try:
                listings = source.fetch()
            except Exception as exc:
                logger.warning("Failed to fetch source %s: %s", source_config.id, exc)
                logger.debug("Source fetch traceback", exc_info=True)
                continue
            results.extend(
                listing for listing in listings if listing_matches(listing, config.criteria, config.neighborhoods)
            )
        return results


def build_source(source_config: SourceConfig, config: MonitorConfig) -> Source:
    if source_config.kind == "craigslist":
        return CraigslistSource(source_config, config)
    if source_config.kind == "webpage":
        return WebPageSource(source_config, config)
    raise ValueError(f"Unsupported source kind: {source_config.kind}")


def _resolve_state_path(config_path: Path, state_path: str) -> Path:
    path = Path(state_path)
    if path.is_absolute():
        return path
    return config_path.parent / path
