from __future__ import annotations

from abc import ABC, abstractmethod

from apartment_monitor.models import ApartmentListing, MonitorConfig, SourceConfig


class Source(ABC):
    def __init__(self, source: SourceConfig, config: MonitorConfig):
        self.source = source
        self.config = config

    @abstractmethod
    def fetch(self) -> list[ApartmentListing]:
        """Fetch current listings from the source."""
