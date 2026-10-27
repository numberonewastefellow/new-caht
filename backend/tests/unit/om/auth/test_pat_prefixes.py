from unittest.mock import MagicMock

import pytest

from om.auth.constants import LEGACY_PAT_PREFIXES
from om.auth.constants import PAT_PREFIX
from om.auth.constants import VALID_PAT_PREFIXES
from om.auth.pat import build_displayable_pat
from om.auth.pat import generate_pat
from om.auth.pat import get_hashed_pat_from_request
from om.auth.pat import hash_pat


def _request(token: str) -> MagicMock:
    req = MagicMock()
    req.headers = {"Authorization": f"Bearer {token}"}
    return req


def test_new_tokens_use_the_om_prefix() -> None:
    assert PAT_PREFIX == "om_pat_"
    assert generate_pat().startswith("om_pat_")


@pytest.mark.parametrize("prefix", ["om_pat_", "onyx_pat_"])
def test_tokens_with_either_prefix_validate(prefix: str) -> None:
    token = prefix + "abcdefghijklmnop"
    assert get_hashed_pat_from_request(_request(token)) == hash_pat(token)


def test_unknown_prefix_is_rejected() -> None:
    assert get_hashed_pat_from_request(_request("other_pat_abcdefghijklmnop")) is None


def test_legacy_prefix_is_listed_but_never_issued() -> None:
    assert LEGACY_PAT_PREFIXES == ("onyx_pat_",)
    assert VALID_PAT_PREFIXES == ["om_pat_", "onyx_pat_"]
    assert not any(generate_pat().startswith(p) for p in LEGACY_PAT_PREFIXES)


@pytest.mark.parametrize(
    "token, expected",
    [("om_pat_abcdXXXXXXXXwxyz", "om_pat_abcd****wxyz"), ("onyx_pat_abcdXXXXXXXXwxyz", "onyx_pat_abcd****wxyz")],
)
def test_display_masks_after_prefix_plus_four(token: str, expected: str) -> None:
    assert build_displayable_pat(token) == expected
