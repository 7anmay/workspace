import pytest

from apartment_monitor.config import ConfigStore
from apartment_monitor.slack_commands import SlackCommandProcessor


def test_set_price_updates_config(tmp_path):
    store = ConfigStore(tmp_path / "config.yaml")
    store.init_default()
    processor = SlackCommandProcessor(store)

    result = processor.handle("apt set 2b max 4800")
    config = store.load()

    assert "2B/2B <= $4,800" in result.message
    assert next(item for item in config.criteria if item.bedrooms == 2).max_price == 4800


def test_set_neighborhoods_updates_config(tmp_path):
    store = ConfigStore(tmp_path / "config.yaml")
    store.init_default()
    processor = SlackCommandProcessor(store)

    processor.handle("apt set neighborhoods Mission Bay, Dogpatch")

    assert store.load().neighborhoods == ["Mission Bay", "Dogpatch"]


def test_add_and_remove_source(tmp_path):
    store = ConfigStore(tmp_path / "config.yaml")
    store.init_default()
    processor = SlackCommandProcessor(store)

    processor.handle(
        'apt add source new-building https://example.com/units name="New Building" neighborhood="Mission Bay"'
    )
    assert any(source.id == "new-building" for source in store.load().sources)

    processor.handle("apt remove source new-building")
    assert not any(source.id == "new-building" for source in store.load().sources)


def test_invalid_set_command_is_reported(tmp_path):
    store = ConfigStore(tmp_path / "config.yaml")
    store.init_default()
    processor = SlackCommandProcessor(store)

    with pytest.raises(ValueError):
        processor.handle("apt set budget cheap")
