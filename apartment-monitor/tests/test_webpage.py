import pytest

from apartment_monitor.models import SourceConfig
from apartment_monitor.sources.webpage import _capture_rendered_html


class FakeTimeout(Exception):
    pass


class FakePage:
    def __init__(self, html="<html><body>partial availability page</body></html>"):
        self.html = html
        self.goto_wait_until = None
        self.waited = False

    def goto(self, url, wait_until, timeout):
        self.goto_wait_until = wait_until
        raise FakeTimeout("navigation never became idle")

    def wait_for_load_state(self, state, timeout):
        raise FakeTimeout("full load never completed")

    def wait_for_timeout(self, timeout):
        self.waited = True

    def content(self):
        return self.html


def test_capture_rendered_html_uses_partial_html_after_navigation_timeout():
    source = SourceConfig(
        id="slow-property-site",
        name="Slow Property Site",
        kind="webpage",
        url="https://example.com/availability",
    )
    page = FakePage()

    html = _capture_rendered_html(page, source, (FakeTimeout,))

    assert "partial availability page" in html
    assert page.goto_wait_until == "domcontentloaded"
    assert page.waited


def test_capture_rendered_html_rejects_empty_partial_html():
    source = SourceConfig(
        id="empty-property-site",
        name="Empty Property Site",
        kind="webpage",
        url="https://example.com/availability",
    )

    with pytest.raises(RuntimeError):
        _capture_rendered_html(FakePage(" "), source, (FakeTimeout,))
