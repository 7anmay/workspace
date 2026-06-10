from apartment_monitor.config import ConfigStore
from apartment_monitor.models import ApartmentListing
from apartment_monitor.monitor import ApartmentMonitor


class FakeSource:
    def __init__(self, listings):
        self.listings = listings

    def fetch(self):
        return self.listings


def test_monitor_returns_only_new_matching_listings(tmp_path, monkeypatch):
    store = ConfigStore(tmp_path / "config.yaml")
    config = store.init_default()
    store.save(
        type(config)(
            interval_minutes=config.interval_minutes,
            criteria=config.criteria,
            neighborhoods=["Mission Bay"],
            sources=config.sources[:1],
            state_path="state.json",
            slack_channel_id=config.slack_channel_id,
        )
    )
    listing = ApartmentListing(
        source_id="equity-855-brannan",
        source_name="855 Brannan",
        title="Mission Bay 2 bed 2 bath",
        url="https://example.com/7a",
        price=4900,
        bedrooms=2,
        bathrooms=2,
        neighborhood="Mission Bay",
    )

    monkeypatch.setattr("apartment_monitor.monitor.build_source", lambda source, cfg: FakeSource([listing]))
    monitor = ApartmentMonitor(store, notify=False)

    assert monitor.run_once() == [listing]
    assert monitor.run_once() == []
