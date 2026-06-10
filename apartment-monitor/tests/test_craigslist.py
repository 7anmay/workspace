from apartment_monitor.config import DEFAULT_CONFIG
from apartment_monitor.models import MonitorConfig, SourceConfig
from apartment_monitor.sources.craigslist import CraigslistSource, parse_craigslist_rss


def test_craigslist_search_urls_include_each_price_cap_and_bedroom_count():
    config = MonitorConfig.from_dict(DEFAULT_CONFIG)
    source = SourceConfig(
        id="craigslist-sf",
        name="Craigslist SF apartments",
        kind="craigslist",
        url="https://sfbay.craigslist.org/search/sfc/apa",
    )

    urls = CraigslistSource(source, config).search_urls()

    assert len(urls) == 2
    assert "max_price=5000" in urls[0]
    assert "min_bedrooms=2" in urls[0]
    assert "max_price=6000" in urls[1]
    assert "min_bedrooms=3" in urls[1]
    assert "min_bathrooms=2" in urls[0]
    assert "Mission+Bay" in urls[0]


def test_parse_craigslist_rss_extracts_listing_fields():
    source = SourceConfig(
        id="craigslist-sf",
        name="Craigslist SF apartments",
        kind="craigslist",
        url="https://sfbay.craigslist.org/search/sfc/apa",
        neighborhood="Mission Bay",
    )
    rss = """
    <rss><channel>
      <item>
        <title>Mission Bay 2 bed 2 bath apartment - $4,900</title>
        <link>https://sfbay.craigslist.org/sfc/apa/example.html</link>
        <guid>cl-123</guid>
        <description>Available now near Caltrain.</description>
      </item>
    </channel></rss>
    """

    listings = parse_craigslist_rss(source, rss)

    assert len(listings) == 1
    assert listings[0].stable_id() == "cl-123"
    assert listings[0].price == 4900
    assert listings[0].bedrooms == 2
    assert listings[0].bathrooms == 2
