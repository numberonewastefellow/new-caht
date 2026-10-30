"""Stream a sub-agent's packets live while it runs in a background thread.

Shared by the sequential and llm_decision orchestration modes.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from collections.abc import Generator
from queue import Empty
from typing import Any

from om.chat.emitter import Emitter
from om.server.query_and_chat.placement import Placement
from om.server.query_and_chat.streaming_models import Packet
from om.server.query_and_chat.streaming_models import WorkflowStepDelta
from om.server.query_and_chat.streaming_models import WorkflowStepReasoningDelta
from om.tools.models import ToolResponse
from om.tools.tool_implementations.agent_tool import AgentTool
from om.utils.logger import setup_logger
from om.utils.threadpool_concurrency import run_in_background
from om.utils.threadpool_concurrency import wait_on_background

logger = setup_logger()

# Packet types emitted by run_llm_step that the workflow engine may need to
# suppress to avoid duplicate content in the frontend.
ANSWER_SUPPRESS_TYPES = frozenset({
    "message_start", "message_delta", "message_end",
})
REASONING_SUPPRESS_TYPES = frozenset({
    "reasoning_start", "reasoning_delta", "reasoning_done",
})
# For sub-agent streaming: suppress both answer text (engine yields its own
# WorkflowStepDelta) and reasoning (would collide with WorkflowStepStart group).
AGENT_SUPPRESS_TYPES = ANSWER_SUPPRESS_TYPES | REASONING_SUPPRESS_TYPES


class StreamingAgentResult:
    """Mutable container to capture ToolResponse + max turn_index from streaming."""

    def __init__(self, start_turn_index: int) -> None:
        self.response: ToolResponse | None = None
        self.exception: Exception | None = None
        self.max_turn_index: int = start_turn_index
        self.cancelled: bool = False


def stream_agent_packets(
    agent_tool: AgentTool,
    placement: Placement,
    emitter: Emitter,
    result: StreamingAgentResult,
    is_connected: Callable[[], bool] | None = None,
    suppress_types: frozenset[str] | None = AGENT_SUPPRESS_TYPES,
    stream_answer_as_step: bool = True,
    stream_reasoning_as_step: bool = True,
    **agent_kwargs: Any,
) -> Generator[Packet, None, None]:
    """Run agent in a background thread, yielding emitter packets in real-time.

    This mirrors the pattern from run_chat_loop_with_state_containers: the
    agent runs in a background thread emitting packets to emitter.bus, while
    the main (generator) thread polls the bus every 50ms and yields each
    packet immediately to the SSE endpoint for real-time streaming.

    Sub-agent answer tokens (``message_delta``) and reasoning tokens
    (``reasoning_delta``) are *translated* — not simply dropped — into
    ``WorkflowStepDelta`` / ``WorkflowStepReasoningDelta`` packets tagged to the
    step's ``placement``, so the step's prose and thinking stream live under the
    step group. The caller then emits the authoritative ``agent_output`` as a
    final ``WorkflowStepDelta(replace=True)`` to reconcile. Set
    ``stream_answer_as_step`` / ``stream_reasoning_as_step`` False to suppress
    (legacy block-per-agent behavior).

    The ToolResponse and max_turn_index are stored in `result` for the caller.
    If is_connected returns False, sets result.cancelled and returns early.
    """

    def _run_agent() -> None:
        try:
            result.response = agent_tool.run(placement, None, **agent_kwargs)
        except Exception as e:
            result.exception = e

    def _process(pkt: Packet) -> Generator[Packet, None, None]:
        """Translate/suppress one sub-agent packet; yield what should stream."""
        otype = pkt.obj.type
        # Answer tokens → live step prose chunk (append). message_start/end carry
        # no step text and are dropped.
        if otype in ANSWER_SUPPRESS_TYPES:
            if stream_answer_as_step and otype == "message_delta":
                text = getattr(pkt.obj, "content", "") or ""
                if text:
                    yield Packet(
                        placement=placement,
                        obj=WorkflowStepDelta(content=text),
                    )
            return
        # Reasoning tokens → live collapsible "thinking" chunk under the step.
        if otype in REASONING_SUPPRESS_TYPES:
            if stream_reasoning_as_step and otype == "reasoning_delta":
                rtext = getattr(pkt.obj, "reasoning", "") or ""
                if rtext:
                    yield Packet(
                        placement=placement,
                        obj=WorkflowStepReasoningDelta(content=rtext),
                    )
            return
        # Any other suppressed type is dropped; everything else (tool packets,
        # citations, etc.) passes through with its own placement, tracking
        # max_turn_index so the next step doesn't collide.
        if suppress_types and otype in suppress_types:
            return
        if pkt.placement.turn_index > result.max_turn_index:
            result.max_turn_index = pkt.placement.turn_index
        yield pkt

    thread = run_in_background(_run_agent)

    cancelled = False
    last_cancel_check = time.monotonic()

    # Poll emitter bus in real-time while agent runs in background
    while True:
        try:
            pkt = emitter.bus.get(timeout=0.05)
        except Empty:
            # Queue empty — check if thread has finished
            if not thread.is_alive():
                break
            # Check stop signal during idle polling
            if is_connected is not None and not is_connected():
                logger.info("Workflow agent cancelled by user")
                cancelled = True
                break
            last_cancel_check = time.monotonic()
            continue

        yield from _process(pkt)

        # Check stop signal periodically even when packets are flowing,
        # matching the pattern from chat_state.py (lines 253-264).
        current_time = time.monotonic()
        if current_time - last_cancel_check >= 0.1:
            if is_connected is not None and not is_connected():
                logger.info("Workflow agent cancelled by user during streaming")
                cancelled = True
                break
            last_cancel_check = current_time

    if cancelled:
        # Don't wait for the background thread — exit fast like chat_state.py
        result.cancelled = True
        return

    # Drain any packets that arrived between the last get() and thread exit
    while True:
        try:
            pkt = emitter.bus.get_nowait()
        except Empty:
            break
        yield from _process(pkt)

    # Propagate any exception from the agent thread
    wait_on_background(thread)
    if result.exception:
        raise result.exception
