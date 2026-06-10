from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any


@dataclass(frozen=True)
class SearchCriterion:
    bedrooms: int
    min_bathrooms: float
    max_price: int
    label: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchCriterion":
        return cls(
            bedrooms=int(data["bedrooms"]),
            min_bathrooms=float(data.get("min_bathrooms", 0)),
            max_price=int(data["max_price"]),
            label=data.get("label"),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "bedrooms": self.bedrooms,
            "min_bathrooms": self.min_bathrooms,
            "max_price": self.max_price,
        }
        if self.label:
            result["label"] = self.label
        return result


@dataclass(frozen=True)
class SourceConfig:
    id: str
    name: str
    kind: str
    url: str
    neighborhood: str | None = None
    enabled: bool = True
    render_js: bool = False
    headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceConfig":
        return cls(
            id=str(data["id"]),
            name=str(data.get("name") or data["id"]),
            kind=str(data.get("kind", "webpage")),
            url=str(data["url"]),
            neighborhood=data.get("neighborhood"),
            enabled=bool(data.get("enabled", True)),
            render_js=bool(data.get("render_js", False)),
            headers=dict(data.get("headers") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "url": self.url,
            "enabled": self.enabled,
        }
        if self.neighborhood:
            result["neighborhood"] = self.neighborhood
        if self.render_js:
            result["render_js"] = self.render_js
        if self.headers:
            result["headers"] = self.headers
        return result


@dataclass(frozen=True)
class ApartmentListing:
    source_id: str
    source_name: str
    title: str
    url: str
    price: int | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    neighborhood: str | None = None
    available_date: str | None = None
    address: str | None = None
    raw_text: str = ""
    external_id: str | None = None

    def stable_id(self) -> str:
        if self.external_id:
            return self.external_id
        key = "|".join(
            [
                self.source_id,
                self.url,
                self.title,
                str(self.price),
                str(self.bedrooms),
                str(self.bathrooms),
                str(self.available_date),
            ]
        )
        return sha256(key.encode("utf-8")).hexdigest()[:24]

    def text_for_matching(self) -> str:
        parts = [
            self.title,
            self.neighborhood or "",
            self.address or "",
            self.raw_text,
            self.source_name,
        ]
        return " ".join(part for part in parts if part).casefold()


@dataclass(frozen=True)
class MonitorConfig:
    interval_minutes: int
    criteria: list[SearchCriterion]
    neighborhoods: list[str]
    sources: list[SourceConfig]
    state_path: str = "state.json"
    slack_channel_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MonitorConfig":
        slack = data.get("slack") or {}
        return cls(
            interval_minutes=int(data.get("interval_minutes", 15)),
            criteria=[SearchCriterion.from_dict(item) for item in data.get("criteria", [])],
            neighborhoods=[str(item) for item in data.get("neighborhoods", [])],
            sources=[SourceConfig.from_dict(item) for item in data.get("sources", [])],
            state_path=str(data.get("state_path", "state.json")),
            slack_channel_id=slack.get("channel_id"),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "interval_minutes": self.interval_minutes,
            "criteria": [criterion.to_dict() for criterion in self.criteria],
            "neighborhoods": self.neighborhoods,
            "sources": [source.to_dict() for source in self.sources],
            "state_path": self.state_path,
        }
        if self.slack_channel_id:
            result["slack"] = {"channel_id": self.slack_channel_id}
        return result
