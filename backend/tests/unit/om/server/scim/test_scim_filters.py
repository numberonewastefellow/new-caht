"""Clean-room tests for the SCIM filter parser + evaluator (RFC 7644 §3.4.2.2)."""

import pytest

from om.server.scim.errors import ScimError
from om.server.scim.filters import parse_filter

USER = {
    "userName": "bjensen@example.com",
    "displayName": "Babs",
    "active": True,
    "emails": [
        {"value": "b@work.com", "type": "work"},
        {"value": "b@home.com", "type": "home"},
    ],
}


@pytest.mark.parametrize(
    "expr,expected",
    [
        ('userName eq "bjensen@example.com"', True),
        ('userName eq "BJENSEN@EXAMPLE.COM"', True),  # case-insensitive
        ('userName eq "nope"', False),
        ('userName eq "bjensen@example.com" and displayName eq "Babs"', True),
        ('userName eq "x" or displayName eq "Babs"', True),
        ('userName sw "bjensen"', True),
        ('userName ew "example.com"', True),
        ('displayName co "ab"', True),
        ("displayName pr", True),
        ("nickName pr", False),
        ("not (active eq false)", True),
        ('emails[type eq "work"]', True),
        ('emails[type eq "work" and value co "work"]', True),
        ('emails[type eq "other"]', False),
        ('(userName eq "a" or userName eq "bjensen@example.com") and active eq true', True),
    ],
)
def test_filter_evaluation(expr: str, expected: bool) -> None:
    assert parse_filter(expr).evaluate(USER) is expected


def test_empty_filter_raises() -> None:
    with pytest.raises(ScimError):
        parse_filter("")


@pytest.mark.parametrize("bad", ['userName eq', 'userName xx "y"', '(userName eq "a"'])
def test_malformed_filter_raises(bad: str) -> None:
    with pytest.raises(ScimError):
        parse_filter(bad)
