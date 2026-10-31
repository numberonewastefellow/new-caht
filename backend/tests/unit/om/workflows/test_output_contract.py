"""An agent step's expected output: the shapes real agents have returned."""

import json

import pytest

from om.workflows.output_contract import check_schema
from om.workflows.output_contract import format_instruction
from om.workflows.output_contract import OutputContractError
from om.workflows.output_contract import read_output
from om.workflows.output_contract import response_format
from om.workflows.output_contract import retry_task

DAYS = {
    "type": "object",
    "properties": {"days": {"type": "array", "items": {"type": "string"}, "minItems": 1}},
    "required": ["days"],
}


class TestReadOutput:
    def test_valid_json_is_kept(self) -> None:
        assert json.loads(read_output('{"days": ["a", "b"]}', DAYS)) == {"days": ["a", "b"]}

    @pytest.mark.parametrize(
        "reply",
        [
            '```json\n{"days": ["a", "b"]}\n```',
            'Here is the outline:\n{"days": ["a", "b"]}\nEnjoy!',
            '{"days": ["a", "b"],}',
            "{'days': ['a', 'b']}",
        ],
    )
    def test_small_mistakes_are_repaired(self, reply: str) -> None:
        assert json.loads(read_output(reply, DAYS)) == {"days": ["a", "b"]}

    @pytest.mark.parametrize(
        "reply",
        [
            # Real replies from the outline agent (workflow runs 584 and 586).
            "Arrive in Manali and settle in  \nExplore Solang Valley  \nVisit Jogini Waterfall",
            '"Arrive in Manali"\n"Snow play at Solang Valley"\n"Jogini Waterfall"',
            '["a", "b"]',
            "",
        ],
    )
    def test_a_reply_that_isnt_the_object_is_refused(self, reply: str) -> None:
        with pytest.raises(OutputContractError, match="isn't a JSON object"):
            read_output(reply, DAYS)

    def test_the_wrong_shape_says_where(self) -> None:
        with pytest.raises(OutputContractError, match="days"):
            read_output('{"days": "a"}', DAYS)
        with pytest.raises(OutputContractError, match="'days' is a required property"):
            read_output('{"other": 1}', DAYS)

    def test_a_cut_off_reply_is_stopped_by_the_schema_where_it_can_be(self) -> None:
        with pytest.raises(OutputContractError, match="too short|non-empty"):
            read_output('{"days": [', DAYS)

    def test_unicode_stays_readable(self) -> None:
        assert "Gubałówka" in read_output('{"days": ["Gubałówka"]}', DAYS)


class TestCheckSchema:
    def test_a_good_schema_passes(self) -> None:
        check_schema(DAYS)

    @pytest.mark.parametrize(
        "schema",
        [
            "not a dict",
            {"type": "array", "items": {"type": "string"}},
            {"type": "object"},
            {"type": "object", "properties": {"a": {"type": "nonsense"}}},
        ],
    )
    def test_an_unusable_schema_is_refused(self, schema: object) -> None:
        with pytest.raises(ValueError):
            check_schema(schema)


class TestResponseFormat:
    def test_strict_providers_get_closed_objects_at_every_level(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "trip": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                },
                "days": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"theme": {"type": "string"}},
                    },
                },
            },
        }
        strict = response_format(schema)["json_schema"]["schema"]
        assert strict["additionalProperties"] is False
        assert strict["required"] == ["trip", "days"]
        assert strict["properties"]["trip"]["required"] == ["name"]
        assert strict["properties"]["days"]["items"]["additionalProperties"] is False

    def test_the_declared_schema_isnt_changed(self) -> None:
        before = json.dumps(DAYS)
        response_format(DAYS)
        assert json.dumps(DAYS) == before


class TestRetryTask:
    def test_it_keeps_the_task_and_says_what_was_wrong(self) -> None:
        task = retry_task("Plan 3 days", "plain lines", "the reply isn't a JSON object", DAYS)
        assert task.startswith("Plan 3 days")
        assert "the reply isn't a JSON object" in task
        assert "plain lines" in task
        assert format_instruction(DAYS) in task
