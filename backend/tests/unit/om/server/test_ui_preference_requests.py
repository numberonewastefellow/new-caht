import pytest
from pydantic import ValidationError

from om.server.manage.models import AccentThemeRequest
from om.server.manage.models import MAX_PINNED_WORKFLOWS
from om.server.manage.models import PinnedWorkflowsRequest


@pytest.mark.parametrize("accent", ["ocean", "emerald", "violet", "neonai"])
def test_known_accents_are_accepted(accent: str) -> None:
    assert AccentThemeRequest(accent_theme=accent).accent_theme == accent


@pytest.mark.parametrize("cleared", [None, "none"])
def test_default_accent_is_stored_as_null(cleared: str | None) -> None:
    assert AccentThemeRequest(accent_theme=cleared).accent_theme is None


def test_unknown_accent_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AccentThemeRequest(accent_theme="hotpink")


def test_pinned_workflows_are_deduped_in_order() -> None:
    request = PinnedWorkflowsRequest(workflow_ids=[5, 3, 5, 9, 3])
    assert request.workflow_ids == [5, 3, 9]


def test_pinned_workflows_are_capped() -> None:
    request = PinnedWorkflowsRequest(workflow_ids=list(range(MAX_PINNED_WORKFLOWS + 50)))
    assert len(request.workflow_ids) == MAX_PINNED_WORKFLOWS
