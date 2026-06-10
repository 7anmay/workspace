from __future__ import annotations

import shlex
from dataclasses import dataclass

from .config import ConfigStore, remove_source, update_criterion, update_neighborhoods, upsert_source
from .models import SourceConfig


@dataclass(frozen=True)
class CommandResult:
    message: str
    run_now: bool = False


class SlackCommandProcessor:
    def __init__(self, store: ConfigStore):
        self.store = store

    def handle(self, text: str) -> CommandResult:
        text = _strip_bot_mention(text).strip()
        if text.startswith("apt "):
            text = text[4:].strip()
        if not text or text in {"help", "?"}:
            return CommandResult(_help_text())

        parts = shlex.split(text)
        command = parts[0].lower()
        config = self.store.load()

        if command == "status":
            return CommandResult(_status_text(config))
        if command in {"run", "search", "check"}:
            return CommandResult("Running an apartment search now.", run_now=True)
        if command == "sources":
            return CommandResult(_sources_text(config.sources))
        if command == "set":
            updated = _handle_set(config, parts[1:])
            self.store.save(updated)
            return CommandResult(_status_text(updated))
        if command == "add" and len(parts) >= 4 and parts[1].lower() == "source":
            source = _parse_source(parts[2:])
            updated = upsert_source(config, source)
            self.store.save(updated)
            return CommandResult(f"Added source `{source.id}`: {source.name}")
        if command == "remove" and len(parts) >= 3 and parts[1].lower() == "source":
            updated = remove_source(config, parts[2])
            self.store.save(updated)
            return CommandResult(f"Removed source `{parts[2]}`.")
        return CommandResult(f"Unknown apartment command. {_help_text()}")


def _handle_set(config, parts):
    if len(parts) >= 3 and parts[0].lower().endswith("b") and parts[1].lower() == "max":
        bedrooms = int(parts[0].lower().removesuffix("b"))
        max_price = int(parts[2].replace("$", "").replace(",", ""))
        return update_criterion(config, bedrooms, max_price)
    if parts and parts[0].lower() in {"areas", "area", "neighborhoods", "neighborhood"}:
        raw = " ".join(parts[1:])
        neighborhoods = [item.strip() for item in raw.split(",") if item.strip()]
        return update_neighborhoods(config, neighborhoods)
    raise ValueError("Expected `set 2b max 4800` or `set neighborhoods Mission Bay, Dogpatch`.")


def _parse_source(parts: list[str]) -> SourceConfig:
    source_id = parts[0]
    url = parts[1]
    options = _options(parts[2:])
    kind = options.pop("kind", "webpage")
    name = options.pop("name", source_id.replace("-", " ").title())
    neighborhood = options.pop("neighborhood", None)
    render_js = options.pop("render_js", "true").lower() in {"1", "true", "yes", "y"}
    return SourceConfig(
        id=source_id,
        name=name,
        kind=kind,
        url=url,
        neighborhood=neighborhood,
        render_js=render_js if kind == "webpage" else False,
    )


def _options(parts: list[str]) -> dict[str, str]:
    options: dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        options[key.lower().replace("-", "_")] = value
    return options


def _status_text(config) -> str:
    criteria = ", ".join(
        f"{item.bedrooms}B/{item.min_bathrooms:g}B <= ${item.max_price:,}" for item in config.criteria
    )
    areas = ", ".join(config.neighborhoods) or "any neighborhood"
    enabled = len([source for source in config.sources if source.enabled])
    return f"Apartment monitor: {criteria}. Areas: {areas}. Sources enabled: {enabled}."


def _sources_text(sources) -> str:
    lines = ["Configured apartment sources:"]
    for source in sources:
        status = "enabled" if source.enabled else "disabled"
        lines.append(f"• `{source.id}` — {source.name} ({source.kind}, {status}) {source.url}")
    return "\n".join(lines)


def _help_text() -> str:
    return (
        "Commands: `apt status`, `apt run`, `apt sources`, `apt set 2b max 4800`, "
        "`apt set neighborhoods Mission Bay, Dogpatch`, "
        "`apt add source id https://example.com name=\"Building\" neighborhood=\"Mission Bay\"`, "
        "`apt remove source id`."
    )


def _strip_bot_mention(text: str) -> str:
    if text.startswith("<@") and ">" in text:
        return text.split(">", 1)[1]
    return text
