"""Slack Block Kit rendering for matched standard answers.

Renders one or more matched answers as Slack blocks: each answer is a markdown
section followed by a "Generate Full Answer" button. The button's ``action_id`` is
the shared :data:`GENERATE_ANSWER_BUTTON_ACTION_ID` handled by the existing button
router (out of WS-D scope); it carries no value — that handler reads the Slack
thread context — so no per-answer payload is encoded here.
"""

from __future__ import annotations

from slack_sdk.models.blocks import ActionsBlock
from slack_sdk.models.blocks import Block
from slack_sdk.models.blocks import ButtonElement
from slack_sdk.models.blocks import DividerBlock
from slack_sdk.models.blocks import SectionBlock
from slack_sdk.models.blocks.basic_components import MarkdownTextObject

from om.db.models import StandardAnswer
from om.onyxbot.slack.constants import GENERATE_ANSWER_BUTTON_ACTION_ID

GENERATE_FULL_ANSWER_TEXT = "Generate Full Answer"


def _answer_section(answer_text: str) -> SectionBlock:
    return SectionBlock(text=MarkdownTextObject(text=answer_text))


def _generate_answer_action() -> ActionsBlock:
    return ActionsBlock(
        elements=[
            ButtonElement(
                action_id=GENERATE_ANSWER_BUTTON_ACTION_ID,
                text=GENERATE_FULL_ANSWER_TEXT,
            )
        ]
    )


def build_answer_blocks(answers: list[StandardAnswer]) -> list[Block]:
    """Compose the Slack blocks for the matched answers (dividers between them)."""

    blocks: list[Block] = []
    for index, answer in enumerate(answers):
        if index > 0:
            blocks.append(DividerBlock())
        blocks.append(_answer_section(answer.answer))
        blocks.append(_generate_answer_action())
    return blocks
