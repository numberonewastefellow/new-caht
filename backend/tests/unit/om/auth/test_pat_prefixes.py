from unittest.mock import MagicMock

import pytest

from om.auth.constants import PAT_PREFIX
from om.auth.pat import build_displayable_pat
from om.auth.pat import generate_pat
from om.auth.pat import get_hashed_pat_from_request
from om.auth.pat import hash_pat


def _request(token: str) -> MagicMock:
    req = MagicMock()
    req.headers = {"Authorization": f"Bearer {token}"}
    return req


def test_tokens_use_the_om_prefix() -> None:
    assert PAT_PREFIX == "om_pat_"
    assert generate_pat().startswith("om_pat_")


def test_om_token_validates() -> None:
    token = "om_pat_abcdefghijklmnop"
    assert get_hashed_pat_from_request(_request(token)) == hash_pat(token)


@pytest.mark.parametrize("token", ["onyx_pat_abcdefghijklmnop", "other_pat_abcdefghijklmnop"])
def test_any_other_prefix_is_rejected(token: str) -> None:
    assert get_hashed_pat_from_request(_request(token)) is None


def test_display_masks_after_prefix_plus_four() -> None:
    assert build_displayable_pat("om_pat_abcdXXXXXXXXwxyz") == "om_pat_abcd****wxyz"
