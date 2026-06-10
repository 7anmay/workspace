from apartment_monitor.filtering import listing_matches
from apartment_monitor.models import SearchCriterion, SourceConfig
from apartment_monitor.parsing import parse_apartment_html, parse_listing_text


def test_parse_apartment_html_extracts_listing_card():
    source = SourceConfig(
        id="test-building",
        name="Test Building",
        kind="webpage",
        url="https://example.com/availability",
        neighborhood="Mission Bay",
    )
    html = """
    <section class="unit-card">
      <h2>Unit 7A</h2>
      <p>2 beds / 2 baths</p>
      <p>$4,850 per month</p>
      <p>Available Jul 1</p>
    </section>
    """

    listings = parse_apartment_html(source, html)

    assert len(listings) == 1
    assert listings[0].price == 4850
    assert listings[0].bedrooms == 2
    assert listings[0].bathrooms == 2
    assert listings[0].neighborhood == "Mission Bay"


def test_parse_listing_text_handles_compact_2b2b_format():
    source = SourceConfig(
        id="craigslist-sf",
        name="Craigslist SF apartments",
        kind="craigslist",
        url="https://sfbay.craigslist.org/search/sfc/apa",
        neighborhood="Dogpatch",
    )

    listing = parse_listing_text(
        source,
        "Dogpatch 2B2B condo $4,700",
        "https://example.com/post",
        "Available now near Crane Cove.",
    )

    assert listing.price == 4700
    assert listing.bedrooms == 2
    assert listing.bathrooms == 2


def test_listing_matches_requested_constraints_and_area():
    source = SourceConfig(
        id="test",
        name="Test",
        kind="webpage",
        url="https://example.com",
        neighborhood="Dogpatch",
    )
    listing = parse_listing_text(source, "Dogpatch 3 bed 2 bath", "https://example.com", "$5,950")

    assert listing_matches(
        listing,
        [SearchCriterion(bedrooms=3, min_bathrooms=2, max_price=6000)],
        ["Mission Bay", "Dogpatch"],
    )


def test_listing_rejects_over_budget():
    source = SourceConfig(
        id="test",
        name="Test",
        kind="webpage",
        url="https://example.com",
        neighborhood="Mission Bay",
    )
    listing = parse_listing_text(source, "Mission Bay 2 bed 2 bath", "https://example.com", "$5,100")

    assert not listing_matches(
        listing,
        [SearchCriterion(bedrooms=2, min_bathrooms=2, max_price=5000)],
        ["Mission Bay"],
    )
