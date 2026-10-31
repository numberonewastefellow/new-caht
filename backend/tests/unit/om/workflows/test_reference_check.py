"""Save-time check of references, and the safe substitution they resolve through."""

import glob
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from om.workflows.inputs import apply_safe_input_mapping
from om.workflows.inputs import find_references
from om.workflows.inputs import render_template
from om.workflows.inputs import UnresolvedReferenceError
from om.workflows.models import WorkflowContext
from om.workflows.reference_check import reference_problem


def _step(
    key: str,
    order: int,
    step_type: str = "agent",
    parent: str | None = None,
    branch: int | None = None,
    mapping: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> Any:
    return SimpleNamespace(
        node_key=key,
        step_type=step_type,
        step_name=key,
        step_order=order,
        output_key=key,
        parent_key=parent,
        branch_index=branch,
        input_mapping=mapping,
        config=config,
        condition=None,
    )


def _reads(text: str) -> dict[str, Any]:
    return {"task": text}


class TestRenderTemplate:
    CONTEXT = WorkflowContext(
        user_input="plan a trip",
        step_outputs={
            "research": '{"items": [{"title": "Goa"}], "n": 2}',
            "research_notes": "NOTES",
            "evil": "$research then $user_input",
        },
    )

    def _render(self, text: str, **variables: Any) -> str:
        return render_template(text, self.CONTEXT, variables)

    def test_user_input_and_outputs(self) -> None:
        assert self._render("Do: $user_input") == "Do: plan a trip"
        assert self._render("$research_notes.output") == "NOTES"

    def test_a_name_that_starts_like_another_is_not_confused(self) -> None:
        assert self._render("$research_notes") == "NOTES"

    def test_follows_a_json_path(self) -> None:
        assert self._render("See $research.output.items[0].title now") == "See Goa now"
        assert self._render("$research.n") == "2"

    def test_follows_a_path_into_a_branch_result_held_as_text(self) -> None:
        context = WorkflowContext(
            user_input="x",
            step_outputs={"par": json.dumps({"Flights": json.dumps([{"v": "BA"}])})},
        )
        assert render_template("$par.output.Flights[0].v", context) == "BA"

    def test_a_substituted_value_is_never_expanded_again(self) -> None:
        assert self._render("$evil") == "$research then $user_input"

    def test_loop_variables_with_a_path(self) -> None:
        loop = {"item": {"title": "Day 1"}, "index": 0}
        assert self._render("Plan $loop.item.title", loop=loop) == "Plan Day 1"
        assert self._render("Number $loop.index", loop=loop) == "Number 0"

    def test_a_whole_object_becomes_json(self) -> None:
        loop = {"item": {"title": "Day 1"}}
        assert json.loads(self._render("$loop.item", loop=loop)) == {"title": "Day 1"}

    def test_a_trailing_full_stop_is_not_part_of_the_reference(self) -> None:
        assert self._render("Read $research_notes.") == "Read NOTES."

    def test_money_and_escapes_are_left_as_text(self) -> None:
        assert self._render("Budget is $500") == "Budget is $500"
        assert self._render("Literal $$research") == "Literal $research"

    def test_an_unknown_reference_fails_clearly(self) -> None:
        with pytest.raises(UnresolvedReferenceError, match="no step output named 'nope'"):
            self._render("$nope")

    def test_a_missing_path_fails_clearly(self) -> None:
        with pytest.raises(UnresolvedReferenceError):
            self._render("$research.output.missing")


class TestApplySafeInputMapping:
    def test_builds_labelled_lines_like_the_legacy_mapping(self) -> None:
        context = WorkflowContext(user_input="hi", step_outputs={})
        assert apply_safe_input_mapping({"task": "Say $user_input", "n": 3}, context, {}) == (
            "task: Say hi\nn: 3"
        )

    def test_no_mapping_uses_the_default_input(self) -> None:
        context = WorkflowContext(user_input="hi", step_outputs={"a": "A"})
        text = apply_safe_input_mapping(None, context, {})
        assert "User request: hi" in text and "A" in text


class TestFindReferences:
    def test_finds_references_and_skips_the_rest(self) -> None:
        text = "$a.output.b[0] and $$escaped, cost $5, then $loop.item."
        assert find_references(text) == ["$a.output.b[0]", "$loop.item"]


class TestReferenceProblem:
    def test_accepts_earlier_steps_and_user_input(self) -> None:
        steps = [
            _step("a", 0, mapping=_reads("$user_input")),
            _step("b", 1, mapping=_reads("$a.output")),
        ]
        assert reference_problem(steps) is None

    def test_refuses_a_later_step(self) -> None:
        steps = [_step("a", 0, mapping=_reads("$b.output")), _step("b", 1)]
        problem = reference_problem(steps)
        assert problem is not None
        assert '"a" reads $b.output' in problem
        assert "$user_input" in problem

    def test_refuses_an_unknown_name(self) -> None:
        assert reference_problem([_step("a", 0, mapping=_reads("$nope"))]) is not None

    def test_refuses_a_sibling_branch(self) -> None:
        steps = [
            _step("p", 0, "parallel"),
            _step("x", 1, parent="p", branch=0),
            _step("y", 2, parent="p", branch=1, mapping=_reads("$x.output")),
        ]
        assert reference_problem(steps) is not None

    def test_accepts_an_earlier_step_in_the_same_branch(self) -> None:
        steps = [
            _step("p", 0, "parallel"),
            _step("x", 1, parent="p", branch=0),
            _step("y", 2, parent="p", branch=0, mapping=_reads("$x.output")),
        ]
        assert reference_problem(steps) is None

    def test_a_branch_can_read_what_ran_before_its_container(self) -> None:
        steps = [
            _step("a", 0),
            _step("p", 1, "parallel"),
            _step("x", 2, parent="p", branch=0, mapping=_reads("$a.output")),
        ]
        assert reference_problem(steps) is None

    def test_after_a_container_its_children_can_be_read(self) -> None:
        steps = [
            _step("p", 0, "parallel"),
            _step("x", 1, parent="p", branch=0),
            _step("after", 2, mapping=_reads("$p.output and $x.output")),
        ]
        assert reference_problem(steps) is None

    def test_loop_variables_only_inside_a_loop(self) -> None:
        inside = [_step("l", 0, "loop"), _step("x", 1, parent="l", branch=0, mapping=_reads("$loop.item.title"))]
        assert reference_problem(inside) is None
        outside = [_step("x", 0, mapping=_reads("$loop.item"))]
        assert reference_problem(outside) is not None

    def test_checks_code_inputs_and_loop_items(self) -> None:
        code = _step("c", 0, "code", config={"inputs": {"x": "$later.output"}})
        assert reference_problem([code, _step("later", 1)]) is not None
        loop = _step("l", 0, "loop", config={"items": "$later.output"})
        assert reference_problem([loop, _step("later", 1)]) is not None

    def test_a_while_loop_condition_can_read_its_own_body(self) -> None:
        steps = [
            _step("l", 0, "loop", config={"mode": "while", "condition_field": "$x.output"}),
            _step("x", 1, parent="l", branch=0),
        ]
        assert reference_problem(steps) is None

    def test_literals_are_fine(self) -> None:
        code = _step("c", 0, "code", config={"inputs": {"x": "plain text", "y": "cost $5"}})
        assert reference_problem([code]) is None


def test_every_sequential_template_passes_the_check() -> None:
    """Deploying a template creates it at schema 2, so its references must hold."""
    root = Path(__file__).parents[3] / "workflow_creator" / "workflows"
    checked = 0
    for path in glob.glob(str(root / "*.json")):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for workflow in data if isinstance(data, list) else [data]:
            if workflow.get("orchestration_mode") != "sequential":
                continue
            checked += 1
            steps = [
                SimpleNamespace(
                    node_key=step.get("node_key") or f"step_{i}",
                    step_type=step.get("step_type", "agent"),
                    step_name=step["step_name"],
                    step_order=step.get("step_order", i),
                    output_key=step.get("output_key") or f"step_{i}",
                    parent_key=step.get("parent_key"),
                    branch_index=step.get("branch_index"),
                    input_mapping=step.get("input_mapping"),
                    config=step.get("config"),
                    condition=step.get("condition"),
                )
                for i, step in enumerate(workflow.get("steps", []))
            ]
            assert reference_problem(steps) is None, f"{Path(path).name}: {reference_problem(steps)}"
    assert checked > 0


def test_a_while_loop_condition_reads_its_own_variables_and_body() -> None:
    config = {"mode": "while", "condition_field": "$loop.index"}
    steps = [
        _step("again", 0, step_type="loop", config=config),
        _step("body", 1, parent="again", branch=0),
    ]
    assert reference_problem(steps) is None
    config["condition_field"] = "$body.output"
    assert reference_problem(steps) is None


def test_a_for_each_loop_cant_read_its_own_body_for_its_items() -> None:
    steps = [
        _step("each", 0, step_type="loop", config={"mode": "for_each", "items": "$body.output"}),
        _step("body", 1, parent="each", branch=0),
    ]
    assert "$body.output" in (reference_problem(steps) or "")


def test_a_loop_has_only_its_own_variables() -> None:
    loop = _step("each", 0, step_type="loop", config={"mode": "for_each", "items": "a"})
    wrong = _step("body", 1, parent="each", branch=0, mapping=_reads("$loop.foo"))
    assert "$loop.foo" in (reference_problem([loop, wrong]) or "")
    right = _step(
        "body", 1, parent="each", branch=0, mapping=_reads("$loop.item.title and $loop.previous")
    )
    assert reference_problem([loop, right]) is None


@pytest.mark.parametrize("wrong", ["$first and more", "$500", "$$5"])
def test_a_value_setting_must_be_one_reference_or_a_literal(wrong: str) -> None:
    def code_input(value: str) -> str | None:
        code = _step("code", 1, step_type="code", config={"inputs": {"x": value}})
        return reference_problem([_step("first", 0), code])

    assert code_input("$first.output.a") is None
    assert code_input("plain text") is None
    assert "single reference" in (code_input(wrong) or "")


def test_a_text_setting_can_mention_amounts_around_references() -> None:
    second = _step("second", 1, mapping=_reads("Spend $500 on $first.output and $$5"))
    assert reference_problem([_step("first", 0), second]) is None


def test_a_routers_condition_is_checked() -> None:
    router = _step("route", 0, step_type="conditional_router")
    router.condition = {"condition_field": "$later.output"}
    assert "$later.output" in (reference_problem([router, _step("later", 1)]) or "")


def test_a_path_through_nothing_is_empty_but_a_wrong_path_still_fails() -> None:
    context = WorkflowContext(user_input="hi", step_outputs={"real": '{"a": 1}'})
    variables = {"skipped": "", "loop": {"previous": None}}
    assert render_template("[$skipped.output.x]", context, variables) == "[]"
    assert render_template("[$loop.previous.x]", context, variables) == "[]"
    with pytest.raises(UnresolvedReferenceError):
        render_template("$real.output.b", context, variables)


class TestDeclaredFields:
    def _code(self) -> Any:
        return _step(
            "plan", 0, step_type="code",
            config={"outputs": [{"name": "days", "type": "integer"}, {"name": "brief"}]},
        )

    def _agent(self) -> Any:
        schema = {"type": "object", "properties": {"days": {"type": "array"}}}
        return _step("outline", 0, config={"output_schema": schema})

    def test_a_declared_field_passes(self) -> None:
        reader = _step("r", 1, mapping=_reads("$plan.output.days and $plan.brief"))
        assert reference_problem([self._code(), reader]) is None

    def test_a_typo_in_a_code_steps_field_is_refused(self) -> None:
        reader = _step("r", 1, mapping=_reads("$plan.output.dayz"))
        problem = reference_problem([self._code(), reader]) or ""
        assert "$plan.output.dayz" in problem and "brief, days" in problem

    def test_a_typo_in_an_agents_field_is_refused(self) -> None:
        reader = _step("r", 1, step_type="code", config={"inputs": {"x": "$outline.output.dayz"}})
        assert "days" in (reference_problem([self._agent(), reader]) or "")

    def test_the_whole_output_is_always_readable(self) -> None:
        reader = _step("r", 1, mapping=_reads("$outline.output"))
        assert reference_problem([self._agent(), reader]) is None

    def test_a_field_deeper_down_isnt_checked(self) -> None:
        reader = _step("r", 1, mapping=_reads("$outline.output.days[0].theme"))
        assert reference_problem([self._agent(), reader]) is None

    def test_a_step_that_declares_nothing_isnt_checked(self) -> None:
        reader = _step("r", 1, mapping=_reads("$free.output.anything"))
        assert reference_problem([_step("free", 0), reader]) is None
