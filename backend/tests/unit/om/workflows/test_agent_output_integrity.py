"""What an agent step returns reaches later steps intact, or fails clearly."""

import json
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from om.chat.citation_processor import DynamicCitationProcessor
from om.chat.models import LlmStepResult
from om.workflows import reference_check
from om.workflows.nodes import agent_tools as agent_tools_module
from om.workflows.nodes.agent_tools import AgentToolCache
from om.workflows.output_contract import _strict
from om.workflows.output_contract import check_schema
from om.workflows.output_contract import OutputContractError
from om.workflows.output_contract import read_output


def _stream(processor: DynamicCitationProcessor, text: str, size: int = 3) -> str:
    out: list[str] = []
    for start in range(0, len(text), size):
        out += [r for r in processor.process_token(text[start : start + size]) if isinstance(r, str)]
    out += [r for r in processor.process_token(None) if isinstance(r, str)]
    return "".join(out)


class TestBracketedNumbers:
    @pytest.mark.parametrize(
        "text",
        [
            '{"ids":[1, 2]}',
            "see section [2] of the policy",
            "matrix [[3]] and [12] here",
            "[1] at the start, [2] and [3], then [4]",
        ],
    )
    def test_a_step_that_found_no_documents_keeps_them(self, text: str) -> None:
        processor = DynamicCitationProcessor(keep_unknown_markers=True)
        assert _stream(processor, text) == text

    def test_chat_still_removes_citations_it_cannot_link(self) -> None:
        assert _stream(DynamicCitationProcessor(), "see [2] here") == "see  here"

    def test_a_step_that_searched_still_removes_them(self) -> None:
        """Its [1] refers to a search result, and agent steps don't show links."""
        processor = DynamicCitationProcessor(keep_unknown_markers=True)
        processor.keep_unknown_markers = False
        assert _stream(processor, "see [2] here") == "see  here"


class TestSchemaCheck:
    GOOD_ITEMS = {"type": "array", "items": {"type": "string"}}

    @pytest.mark.parametrize(
        "schema,mentions",
        [
            ({"type": "object", "properties": {"days": {"type": "array"}}}, "days"),
            ({"type": "object", "properties": {"a": {"type": "object"}}}, "a"),
            (
                {
                    "type": "object",
                    "properties": {"a": {"type": "array", "items": {"type": "object"}}},
                },
                "a",
            ),
            (
                {
                    "type": "object",
                    "properties": {"a": {"anyOf": [{"type": "string"}, {"type": "object"}]}},
                },
                "a",
            ),
            (
                {"type": "object", "properties": {"a": {"oneOf": [{"type": "string"}]}}},
                "oneOf",
            ),
            ({"type": "object", "properties": {"a": {}}}, "a"),
            ({"type": "object", "properties": {"a": True}}, "a"),
            (
                {
                    "type": "object",
                    "properties": {"a": {"$ref": "#/$defs/x"}},
                    "$defs": {"x": {"type": "object"}},
                },
                "x",
            ),
            (
                {
                    "type": "object",
                    "properties": {"a": {"type": "array", "anyOf": [{"type": "array", "items": {"type": "string"}}]}},
                },
                "a",
            ),
        ],
    )
    def test_refused_at_save(self, schema: dict[str, Any], mentions: str) -> None:
        with pytest.raises(ValueError, match=mentions):
            check_schema(schema)

    @pytest.mark.parametrize(
        "schema",
        [
            {"type": "object", "properties": {"days": GOOD_ITEMS}},
            {
                "type": "object",
                "properties": {
                    "a": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "b": {"type": ["string", "null"]},
                    "c": {"type": "string", "enum": ["x", "y"]},
                    "d": {
                        "type": "object",
                        "properties": {"e": {"type": "array", "items": {"type": "number"}}},
                    },
                },
            },
        ],
    )
    def test_accepted(self, schema: dict[str, Any]) -> None:
        check_schema(schema)

    def test_the_error_message_shows_a_form_that_works(self) -> None:
        with pytest.raises(ValueError) as refused:
            check_schema({"type": "array"})
        example = str(refused.value)[str(refused.value).index("{") :]
        check_schema(json.loads(example))

    def test_objects_inside_any_of_are_closed_for_strict_providers(self) -> None:
        strict = _strict(
            {
                "type": "object",
                "properties": {
                    "a": {
                        "anyOf": [
                            {"type": "object", "properties": {"b": {"type": "string"}}},
                            {"type": "null"},
                        ]
                    }
                },
            }
        )
        closed = strict["properties"]["a"]["anyOf"][0]
        assert closed["additionalProperties"] is False
        assert closed["required"] == ["b"]


class TestOldReferenceFormat:
    @staticmethod
    def _step(key: str, order: int, mapping: Any = None, condition: Any = None) -> Any:
        return MagicMock(
            step_type="agent",
            step_name=key,
            step_order=order,
            output_key=key,
            parent_key=None,
            branch_index=None,
            input_mapping=mapping,
            config=None,
            condition=condition,
        )

    def test_a_field_in_text_is_refused_too(self) -> None:
        steps = [self._step("s", 0), self._step("r", 1, mapping={"task": "$s.output.status"})]
        assert "$s.output.status" in (reference_check.old_format_problem(steps) or "")

    def test_a_field_reference_is_refused_with_the_way_forward(self) -> None:
        steps = [
            self._step("s", 0),
            self._step("r", 1, condition={"condition_field": "$s.output.status"}),
        ]
        problem = reference_check.old_format_problem(steps)
        assert problem is not None
        assert "$s.output.status" in problem
        assert "Upgrade" in problem

    @pytest.mark.parametrize(
        "text",
        ["$s", "$s.output", "$s.pdf", "costs $500.00", "ask $user_input", "$other.output.status"],
    )
    def test_what_the_old_format_can_read_is_fine(self, text: str) -> None:
        steps = [self._step("s", 0), self._step("r", 1, mapping={"task": text})]
        assert reference_check.old_format_problem(steps) is None


def test_steps_with_a_schema_keep_their_text_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        agent_tools_module, "AgentTool", lambda **kwargs: captured.update(kwargs) or MagicMock()
    )
    monkeypatch.setattr(agent_tools_module, "load_step_agent", lambda *_: MagicMock(tools=[]))
    cache = AgentToolCache(db_session=MagicMock(), user=MagicMock(), emitter=MagicMock())
    monkeypatch.setattr(cache, "_llm_for", lambda *_: MagicMock())
    schema = {"type": "object", "properties": {"a": {"type": "string"}}}

    cache.get(MagicMock(node_key="a"), MagicMock(output_schema=schema, tool_ids_override=None))
    assert captured["exact_output"] is True

    cache.get(MagicMock(node_key="b"), MagicMock(output_schema=None, tool_ids_override=None))
    assert captured["exact_output"] is False


def test_the_step_result_carries_why_the_reply_ended() -> None:
    result = LlmStepResult(reasoning=None, answer="x", tool_calls=None, finish_reason="length")
    assert result.finish_reason == "length"


def test_a_failed_run_still_saves_its_steps() -> None:
    """The engine raising mustn't lose the steps that already ran."""
    from om.chat import message_handler
    from om.server.query_and_chat.streaming_models import Packet
    from om.server.query_and_chat.streaming_models import WorkflowStepStart
    from om.server.query_and_chat.placement import Placement

    def exploding_run(**_: Any) -> Any:
        yield Packet(
            placement=Placement(turn_index=0),
            obj=WorkflowStepStart(step_name="First", step_order=0),
        )
        raise RuntimeError("engine broke")

    with (
        patch("om.workflows.workflow_engine.run_workflow", exploding_run),
        patch.object(message_handler, "save_chat_turn") as save,
    ):
        stream = message_handler._run_workflow_and_save(
            workflow=MagicMock(),
            user_message="go",
            emitter=MagicMock(),
            db_session=MagicMock(),
            user=MagicMock(),
            is_connected=None,
            chat_session_id=None,
            assistant_message=MagicMock(id=1),
        )
        with pytest.raises(RuntimeError, match="engine broke"):
            list(stream)

    save.assert_called_once()
    assert "internal error" in save.call_args.kwargs["message_text"]
    assert "engine broke" not in save.call_args.kwargs["message_text"]
    saved_steps = save.call_args.kwargs["tool_calls"]
    assert any("First" in json.dumps(str(call)) for call in saved_steps)


class TestPartialRepliesAreNotCompleted:
    """A provider may not say it hit a limit, so the reply itself is checked too."""

    SCHEMA = {
        "type": "object",
        "properties": {"days": {"type": "array", "items": {"type": "string"}}},
        "required": ["days"],
    }

    @pytest.mark.parametrize(
        "reply",
        [
            '{"days":["a","b","Day thr',
            '{"days":["a","b"',
            '{"days":[',
            '```json\n{"days":["a"',
            '{"days":["a \\" b',
        ],
    )
    def test_a_reply_that_stops_mid_structure_is_refused(self, reply: str) -> None:
        with pytest.raises(OutputContractError, match="stops before"):
            read_output(reply, self.SCHEMA)

    @pytest.mark.parametrize(
        "reply",
        [
            '{"days": ["a"]}',
            '```json\n{"days": ["a"]}\n```',
            'Here it is: {"days": ["a"]} Hope that helps',
            '{"days": ["a",],}',
            "{'days': ['a']}",
            '{"days": ["a ] b { c"]}',
        ],
    )
    def test_small_mistakes_are_still_repaired(self, reply: str) -> None:
        assert json.loads(read_output(reply, self.SCHEMA))["days"][0].startswith("a")


def test_a_step_failure_is_explained_when_the_chat_is_reloaded() -> None:
    from om.chat.message_handler import _stopped_message
    from om.workflows.blocks import WorkflowNodeError

    assert "was cut off" in _stopped_message([WorkflowNodeError("Step was cut off")])
    assert _stopped_message([]) == ""


def test_llm_step_reports_why_the_reply_ended() -> None:
    """Through the real step code, not just the result model."""
    from om.chat.llm_step import run_llm_step_pkt_generator
    from om.chat.models import LlmStepResult as Result
    from om.llm.interfaces import ToolChoiceOptions
    from om.llm.model_response import Delta
    from om.llm.model_response import ModelResponseStream
    from om.llm.model_response import StreamingChoice
    from om.server.query_and_chat.placement import Placement

    def chunk(content: str, finish: str | None) -> ModelResponseStream:
        return ModelResponseStream(
            id="1",
            created="0",
            choice=StreamingChoice(delta=Delta(content=content), finish_reason=finish),
        )

    llm = MagicMock()
    llm.config.model_name = "gpt-4o-mini"
    llm.config.model_provider = "openai"
    llm.stream.return_value = iter([chunk("par", None), chunk("tial", "length")])
    generator = run_llm_step_pkt_generator(
        history=[],
        tool_definitions=[],
        tool_choice=ToolChoiceOptions.NONE,
        llm=llm,
        placement=Placement(turn_index=0),
        state_container=None,
        citation_processor=None,
    )
    result: Result | None = None
    while result is None:
        try:
            next(generator)
        except StopIteration as stop:
            result = stop.value[0]
    assert result.finish_reason == "length"
    assert result.answer == "partial"
