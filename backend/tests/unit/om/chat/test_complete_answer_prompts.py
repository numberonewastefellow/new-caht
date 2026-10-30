"""COMPLETE_ANSWER_REMINDER / MULTI_PART_ANSWER_GUIDANCE in the chat prompt
builders (build_reminder_message, build_system_prompt)."""

from collections.abc import Iterator
from typing import Any
from unittest.mock import patch

import pytest

from om.chat.prompt_utils import build_reminder_message
from om.chat.prompt_utils import build_system_prompt
from om.prompts.chat_prompts import CITATION_GUIDANCE_REPLACEMENT_PAT
from om.prompts.chat_prompts import CITATION_REMINDER
from om.prompts.chat_prompts import COMPLETE_ANSWER_REMINDER
from om.prompts.chat_prompts import DEFAULT_SYSTEM_PROMPT
from om.prompts.chat_prompts import FILE_REMINDER
from om.prompts.chat_prompts import LAST_CYCLE_CITATION_REMINDER
from om.prompts.chat_prompts import MULTI_PART_ANSWER_GUIDANCE
from om.prompts.chat_prompts import REQUIRE_CITATION_GUIDANCE

_FLAG = "om.prompts.prompt_utils.ENABLE_COMPLETE_ANSWER_PROMPTS"


@pytest.fixture(autouse=True)
def _no_company_context() -> Iterator[None]:
    with patch("om.chat.prompt_utils.get_company_context", return_value=None):
        yield


def _set_flag(enabled: bool) -> Any:
    return patch(_FLAG, enabled)


# ---- build_reminder_message ------------------------------------------------


def test_reminder_cite_on_adds_complete_answer_after_citation() -> None:
    with _set_flag(True):
        reminder = build_reminder_message(
            reminder_text=None,
            include_citation_reminder=True,
            include_file_reminder=False,
            is_last_cycle=False,
        )
    assert reminder == CITATION_REMINDER + "\n\n" + COMPLETE_ANSWER_REMINDER


def test_reminder_cite_off_has_no_complete_answer() -> None:
    with _set_flag(True):
        reminder = build_reminder_message(
            reminder_text="Do the task.",
            include_citation_reminder=False,
            include_file_reminder=False,
            is_last_cycle=False,
        )
    assert reminder == "Do the task."


def test_reminder_order_task_lastcycle_citation_complete_file() -> None:
    with _set_flag(True):
        reminder = build_reminder_message(
            reminder_text="  Task prompt.  ",
            include_citation_reminder=True,
            include_file_reminder=True,
            is_last_cycle=True,
        )
    assert reminder is not None
    parts = [
        "Task prompt.",
        LAST_CYCLE_CITATION_REMINDER,
        CITATION_REMINDER,
        COMPLETE_ANSWER_REMINDER,
        FILE_REMINDER,
    ]
    assert reminder == "\n\n".join(parts)


def test_reminder_flag_off_is_previous_output() -> None:
    with _set_flag(False):
        reminder = build_reminder_message(
            reminder_text=None,
            include_citation_reminder=True,
            include_file_reminder=False,
            is_last_cycle=True,
        )
    assert reminder == LAST_CYCLE_CITATION_REMINDER + "\n\n" + CITATION_REMINDER
    assert COMPLETE_ANSWER_REMINDER not in reminder


def test_reminder_nothing_returns_none() -> None:
    with _set_flag(True):
        assert (
            build_reminder_message(
                reminder_text=None,
                include_citation_reminder=False,
                include_file_reminder=False,
                is_last_cycle=False,
            )
            is None
        )


# ---- build_system_prompt ---------------------------------------------------


def test_default_prompt_no_search_has_no_guidance() -> None:
    with _set_flag(True):
        prompt = build_system_prompt(DEFAULT_SYSTEM_PROMPT, should_cite_documents=False)
    assert REQUIRE_CITATION_GUIDANCE not in prompt
    assert MULTI_PART_ANSWER_GUIDANCE not in prompt
    assert CITATION_GUIDANCE_REPLACEMENT_PAT not in prompt


def test_default_prompt_with_search_inserts_both_at_placeholder() -> None:
    # DEFAULT_SYSTEM_PROMPT carries the {{CITATION_GUIDANCE}} placeholder.
    with _set_flag(True):
        prompt = build_system_prompt(DEFAULT_SYSTEM_PROMPT, should_cite_documents=True)
    assert prompt.count(REQUIRE_CITATION_GUIDANCE) == 1
    assert prompt.count(MULTI_PART_ANSWER_GUIDANCE) == 1
    assert (
        REQUIRE_CITATION_GUIDANCE + MULTI_PART_ANSWER_GUIDANCE in prompt
    ), "multi-part guidance must follow the citation guidance directly"
    # inserted where the placeholder was: before the Response Style section
    assert prompt.index(MULTI_PART_ANSWER_GUIDANCE) < prompt.index("# Response Style")


def test_custom_prompt_without_placeholder_appends_both() -> None:
    base = "You are a helpful bot."
    with _set_flag(True):
        prompt = build_system_prompt(base, should_cite_documents=True)
    assert prompt.endswith(REQUIRE_CITATION_GUIDANCE + MULTI_PART_ANSWER_GUIDANCE)


def test_custom_prompt_without_placeholder_no_search() -> None:
    base = "You are a helpful bot."
    with _set_flag(True):
        prompt = build_system_prompt(base, should_cite_documents=False)
    assert prompt == base


def test_flag_off_is_previous_output() -> None:
    base = "You are a helpful bot."
    with _set_flag(False):
        appended = build_system_prompt(base, should_cite_documents=True)
        placeholder = build_system_prompt(
            DEFAULT_SYSTEM_PROMPT, should_cite_documents=True
        )
    assert appended == base + REQUIRE_CITATION_GUIDANCE
    assert MULTI_PART_ANSWER_GUIDANCE not in placeholder
    assert placeholder.count(REQUIRE_CITATION_GUIDANCE) == 1


def test_prompt_already_containing_guidance_is_not_duplicated() -> None:
    base = (
        "You are a helpful bot."
        + REQUIRE_CITATION_GUIDANCE
        + MULTI_PART_ANSWER_GUIDANCE
    )
    with _set_flag(True):
        prompt = build_system_prompt(base, should_cite_documents=True)
    assert prompt.count(REQUIRE_CITATION_GUIDANCE) == 1
    assert prompt.count(MULTI_PART_ANSWER_GUIDANCE) == 1


def test_placeholder_prompt_already_containing_multi_part_not_duplicated() -> None:
    base = (
        f"Intro.{CITATION_GUIDANCE_REPLACEMENT_PAT}\nRules."
        + MULTI_PART_ANSWER_GUIDANCE
    )
    with _set_flag(True):
        prompt = build_system_prompt(base, should_cite_documents=True)
    assert prompt.count(MULTI_PART_ANSWER_GUIDANCE) == 1
    assert prompt.count(REQUIRE_CITATION_GUIDANCE) == 1


def test_include_all_guidance_reserves_tokens_for_new_text() -> None:
    # calculate_reserved_tokens builds this fake prompt to reserve tokens
    with _set_flag(True):
        prompt = build_system_prompt(
            DEFAULT_SYSTEM_PROMPT,
            datetime_aware=True,
            should_cite_documents=True,
            include_all_guidance=True,
        )
    assert MULTI_PART_ANSWER_GUIDANCE in prompt
