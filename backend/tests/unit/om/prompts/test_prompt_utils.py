from unittest.mock import patch

from om.prompts.chat_prompts import CITATION_GUIDANCE_REPLACEMENT_PAT
from om.prompts.chat_prompts import MULTI_PART_ANSWER_GUIDANCE
from om.prompts.chat_prompts import REQUIRE_CITATION_GUIDANCE
from om.prompts.constants import REMINDER_TAG_DESCRIPTION
from om.prompts.prompt_utils import replace_citation_guidance_tag
from om.prompts.prompt_utils import replace_reminder_tag


def test_replace_reminder_tag_pattern() -> None:
    prompt = "Some text {{REMINDER_TAG_DESCRIPTION}} more text"
    result = replace_reminder_tag(prompt)
    assert "{{REMINDER_TAG_DESCRIPTION}}" not in result
    assert REMINDER_TAG_DESCRIPTION in result


def test_replace_reminder_tag_no_pattern() -> None:
    prompt = "Some text without any pattern"
    result = replace_reminder_tag(prompt)
    assert result == prompt


# ---- replace_citation_guidance_tag: placeholder branch + multi-part guidance ----

_FLAG = "om.prompts.prompt_utils.ENABLE_COMPLETE_ANSWER_PROMPTS"
_TAGGED = f"Intro.{CITATION_GUIDANCE_REPLACEMENT_PAT}\nMore."


def test_placeholder_with_citations_inserts_citation_and_multi_part() -> None:
    with patch(_FLAG, True):
        result, append = replace_citation_guidance_tag(
            _TAGGED, should_cite_documents=True
        )
    assert append is False
    assert result == (
        "Intro." + REQUIRE_CITATION_GUIDANCE + MULTI_PART_ANSWER_GUIDANCE + "\nMore."
    )


def test_placeholder_without_citations_is_emptied() -> None:
    with patch(_FLAG, True):
        result, append = replace_citation_guidance_tag(
            _TAGGED, should_cite_documents=False
        )
    assert append is False
    assert result == "Intro.\nMore."


def test_placeholder_flag_off_inserts_citation_only() -> None:
    with patch(_FLAG, False):
        result, _ = replace_citation_guidance_tag(_TAGGED, should_cite_documents=True)
    assert result == "Intro." + REQUIRE_CITATION_GUIDANCE + "\nMore."


def test_no_placeholder_signals_append_unless_already_present() -> None:
    with patch(_FLAG, True):
        _, append = replace_citation_guidance_tag(
            "Plain prompt.", should_cite_documents=True
        )
        _, append_dup = replace_citation_guidance_tag(
            "Plain prompt." + REQUIRE_CITATION_GUIDANCE, should_cite_documents=True
        )
    assert append is True
    assert append_dup is False
