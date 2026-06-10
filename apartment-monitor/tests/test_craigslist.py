import httpx

from apartment_monitor.config import DEFAULT_CONFIG
from apartment_monitor.models import MonitorConfig, SourceConfig
from apartment_monitor.sources import craigslist
from apartment_monitor.sources.craigslist import CraigslistSource, parse_craigslist_html, parse_craigslist_rss


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


def test_parse_craigslist_html_extracts_modern_result_card():
    source = SourceConfig(
        id="craigslist-sf",
        name="Craigslist SF apartments",
        kind="craigslist",
        url="https://sfbay.craigslist.org/search/sfc/apa",
        neighborhood="Dogpatch",
    )
    html = """
    <ol>
      <li class="cl-static-search-result" data-pid="789">
        <a href="https://sfbay.craigslist.org/sfc/apa/789.html">
          <div class="title">Dogpatch 3 bed 2 bath apartment</div>
          <div class="price">$5,800</div>
          <div class="location">Dogpatch</div>
        </a>
      </li>
    </ol>
    """

    listings = parse_craigslist_html(source, html)

    assert len(listings) == 1
    assert listings[0].stable_id() == "craigslist-789"
    assert listings[0].price == 5800
    assert listings[0].bedrooms == 3
    assert listings[0].bathrooms == 2


def test_craigslist_fetch_falls_back_to_html_on_rss_403(monkeypatch):
    config = MonitorConfig.from_dict(DEFAULT_CONFIG)
    source = SourceConfig(
        id="craigslist-sf",
        name="Craigslist SF apartments",
        kind="craigslist",
        url="https://sfbay.craigslist.org/search/sfc/apa",
    )
    request = httpx.Request("GET", "https://sfbay.craigslist.org/search/sfc/apa")
    response = httpx.Response(403, request=request)

    def blocked_rss(source_config, url):
        raise httpx.HTTPStatusError("blocked", request=request, response=response)

    monkeypatch.setattr(craigslist, "_fetch_rss", blocked_rss)
    monkeypatch.setattr(
        craigslist,
        "_fetch_html_with_warning",
        lambda source_config, url: [
            parse_craigslist_html(
                source_config,
                """
                <li class="cl-static-search-result" data-pid="123">
                  <a href="https://sfbay.craigslist.org/sfc/apa/123.html">
                    <div class="title">Mission Bay 2 bed 2 bath apartment</div>
                    <div class="price">$4,900</div>
                  </a>
                </li>
                """,
            )[0]
        ],
    )

    listings = CraigslistSource(source, config).fetch()

    assert listings
    assert listings[0].price == 4900
