from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import MonitorConfig, SearchCriterion, SourceConfig


DEFAULT_CONFIG: dict[str, Any] = {
    "interval_minutes": 15,
    "state_path": "state.json",
    "neighborhoods": [
        "Mission Bay",
        "Dogpatch",
        "SoMa",
        "South Beach",
        "Potrero Hill",
        "Rincon Hill",
        "Design District",
    ],
    "criteria": [
        {"label": "2B2B under $5K", "bedrooms": 2, "min_bathrooms": 2, "max_price": 5000},
        {"label": "3B2B under $6K", "bedrooms": 3, "min_bathrooms": 2, "max_price": 6000},
    ],
    "sources": [
        {
            "id": "equity-855-brannan",
            "name": "855 Brannan",
            "kind": "webpage",
            "url": "https://www.equityapartments.com/san-francisco/soma/855-brannan-apartments##unit-availability-tile",
            "neighborhood": "SoMa",
            "render_js": True,
        },
        {
            "id": "quincy-sf",
            "name": "The Quincy",
            "kind": "webpage",
            "url": "https://www.quincysf.com/floor-plans-and-availability/",
            "neighborhood": "SoMa",
            "render_js": True,
        },
        {
            "id": "avalon-mission-bay",
            "name": "Avalon at Mission Bay",
            "kind": "webpage",
            "url": "https://www.avaloncommunities.com/california/san-francisco-apartments/avalon-at-mission-bay/#community-unit-listings",
            "neighborhood": "Mission Bay",
            "render_js": True,
        },
        {
            "id": "craigslist-sf",
            "name": "Craigslist SF apartments",
            "kind": "craigslist",
            "url": "https://sfbay.craigslist.org/search/sfc/apa",
            "neighborhood": "San Francisco",
        },
    ],
}


class ConfigStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> MonitorConfig:
        with self.path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return MonitorConfig.from_dict(data)

    def save(self, config: MonitorConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(config.to_dict(), handle, sort_keys=False)

    def init_default(self, overwrite: bool = False) -> MonitorConfig:
        if self.path.exists() and not overwrite:
            return self.load()
        config = MonitorConfig.from_dict(DEFAULT_CONFIG)
        self.save(config)
        return config


def update_criterion(config: MonitorConfig, bedrooms: int, max_price: int) -> MonitorConfig:
    criteria = []
    replaced = False
    for criterion in config.criteria:
        if criterion.bedrooms == bedrooms:
            criteria.append(
                SearchCriterion(
                    bedrooms=criterion.bedrooms,
                    min_bathrooms=criterion.min_bathrooms,
                    max_price=max_price,
                    label=f"{bedrooms}B{int(criterion.min_bathrooms)}B under ${max_price:,}",
                )
            )
            replaced = True
        else:
            criteria.append(criterion)
    if not replaced:
        criteria.append(
            SearchCriterion(
                bedrooms=bedrooms,
                min_bathrooms=2,
                max_price=max_price,
                label=f"{bedrooms}B2B under ${max_price:,}",
            )
        )
    return _replace_config(config, criteria=criteria)


def update_neighborhoods(config: MonitorConfig, neighborhoods: list[str]) -> MonitorConfig:
    return _replace_config(config, neighborhoods=neighborhoods)


def upsert_source(config: MonitorConfig, source: SourceConfig) -> MonitorConfig:
    sources = [item for item in config.sources if item.id != source.id]
    sources.append(source)
    return _replace_config(config, sources=sources)


def remove_source(config: MonitorConfig, source_id: str) -> MonitorConfig:
    return _replace_config(config, sources=[item for item in config.sources if item.id != source_id])


def set_slack_channel(config: MonitorConfig, channel_id: str) -> MonitorConfig:
    return _replace_config(config, slack_channel_id=channel_id)


def _replace_config(
    config: MonitorConfig,
    *,
    criteria: list[SearchCriterion] | None = None,
    neighborhoods: list[str] | None = None,
    sources: list[SourceConfig] | None = None,
    slack_channel_id: str | None = None,
) -> MonitorConfig:
    return MonitorConfig(
        interval_minutes=config.interval_minutes,
        criteria=criteria if criteria is not None else config.criteria,
        neighborhoods=neighborhoods if neighborhoods is not None else config.neighborhoods,
        sources=sources if sources is not None else config.sources,
        state_path=config.state_path,
        slack_channel_id=slack_channel_id if slack_channel_id is not None else config.slack_channel_id,
    )
