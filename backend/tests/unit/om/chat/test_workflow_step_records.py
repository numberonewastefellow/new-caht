"""Packets of parallel branches interleave; each goes to its own step's record."""

from om.chat.message_handler import open_step_at


def test_no_step_open() -> None:
    assert open_step_at({}, 5) is None


def test_a_sequential_step_takes_its_sub_turns() -> None:
    step = {"step_name": "a"}
    assert open_step_at({3: step}, 3) is step
    assert open_step_at({3: step}, 9) is step


def test_a_packet_before_any_open_step_belongs_to_none() -> None:
    assert open_step_at({3: {"step_name": "a"}}, 2) is None


def test_branches_running_together_keep_their_packets() -> None:
    first, second = {"step_name": "first"}, {"step_name": "second"}
    open_steps = {1000: first, 2000: second}
    assert open_step_at(open_steps, 1000) is first
    assert open_step_at(open_steps, 2000) is second
    assert open_step_at(open_steps, 1004) is first
    assert open_step_at(open_steps, 2004) is second
