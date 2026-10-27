from pathlib import Path
from urllib.parse import urlparse

import pytest

from om.configs.constants import DocumentSource
from om.ombot.slack import icons
from om.ombot.slack.icons import source_to_img_link

WEB_PUBLIC = Path(__file__).resolve().parents[5] / "web" / "public"


def test_every_icon_is_a_real_file_served_by_our_web_app() -> None:
    missing = [p for p in {*icons._SOURCE_ICONS.values(), icons._DEFAULT_ICON} if not (WEB_PUBLIC / p).is_file()]
    assert not missing, f"icon files missing from web/public: {missing}"


def test_icon_urls_use_web_domain_and_never_third_party_hosts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(icons, "WEB_DOMAIN", "https://om.example.test/")
    for source in DocumentSource:
        url = source_to_img_link(source)
        assert url.startswith("https://om.example.test/") and not url.startswith("https://om.example.test//")
        assert urlparse(url).hostname == "om.example.test"  # never a third-party host


def test_unknown_source_gets_default_icon(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(icons, "WEB_DOMAIN", "https://om.example.test")
    assert source_to_img_link("definitely_not_a_source") == "https://om.example.test/slackbot/File.png"
