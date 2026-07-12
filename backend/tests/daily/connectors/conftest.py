from collections.abc import Generator
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest



@pytest.fixture
def mock_get_unstructured_api_key() -> Generator[MagicMock, None, None]:
    with patch(
        "om.file_processing.extract_file_text.get_unstructured_api_key",
        return_value=None,
    ) as mock:
        yield mock


@pytest.fixture
def set_ee_on() -> Generator[None, None, None]:
    """No-op. Kept so the tests that request it keep working.

    Perm syncing used to be EE-gated, so these tests had to flip global_version on and
    back off. There is one edition now and the feature is always available, so there is
    nothing to toggle -- and nothing to restore afterwards.
    """
    yield
