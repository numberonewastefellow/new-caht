"""Arize Phoenix tracing processor using OpenTelemetry OTLP export.

Phoenix accepts standard OTLP traces, so we translate our internal tracing
framework spans into OTel spans and export them via OTLP/HTTP.  No Phoenix
SDK is needed — only the standard ``opentelemetry`` packages that are
already in the dependency tree.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any
from typing import Optional

from opentelemetry import trace as otel_trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import StatusCode

from onyx.tracing.framework.processor_interface import TracingProcessor
from onyx.tracing.framework.span_data import AgentSpanData
from onyx.tracing.framework.span_data import FunctionSpanData
from onyx.tracing.framework.span_data import GenerationSpanData
from onyx.tracing.framework.span_data import SpanData
from onyx.tracing.framework.spans import Span
from onyx.tracing.framework.traces import Trace

logger = logging.getLogger(__name__)

# Stale entry TTL — if a trace/span hasn't been closed after this many
# seconds, its tracking dicts are eligible for cleanup to prevent leaks.
_STALE_ENTRY_TTL_SECONDS = 600  # 10 minutes


class PhoenixTracingProcessor(TracingProcessor):
    """TracingProcessor that exports traces to Arize Phoenix via OTLP/HTTP.

    Args:
        endpoint: The Phoenix OTLP collector endpoint
                  (e.g. ``http://phoenix:6006/v1/traces``).
        enable_masking: Whether to mask sensitive data before sending.
        service_name: OTel resource service name for this backend.
        max_queue_size: Maximum number of spans queued before dropping.
        max_export_batch_size: Batch size for OTLP exports.
        schedule_delay_millis: Delay between batch exports in ms.
    """

    def __init__(
        self,
        endpoint: str,
        enable_masking: bool = True,
        service_name: str = "virtualai-backend",
        max_queue_size: int = 4096,
        max_export_batch_size: int = 512,
        schedule_delay_millis: int = 2000,
    ) -> None:
        self._enable_masking = enable_masking
        self._lock = threading.Lock()

        # Map our framework IDs → OTel span objects
        self._otel_spans: dict[str, otel_trace.Span] = {}
        # Root span per trace (to set input/output)
        self._trace_root_spans: dict[str, otel_trace.Span] = {}
        self._first_input: dict[str, Any] = {}
        self._last_output: dict[str, Any] = {}
        # Timestamps for stale entry cleanup
        self._trace_timestamps: dict[str, float] = {}
        self._span_timestamps: dict[str, float] = {}

        # Build an isolated OTel TracerProvider that exports to Phoenix
        resource = Resource.create({"service.name": service_name})
        exporter = OTLPSpanExporter(endpoint=endpoint)
        self._provider = TracerProvider(resource=resource)
        self._provider.add_span_processor(
            BatchSpanProcessor(
                exporter,
                max_queue_size=max_queue_size,
                max_export_batch_size=max_export_batch_size,
                schedule_delay_millis=schedule_delay_millis,
            )
        )
        self._tracer = self._provider.get_tracer("virtualai.tracing")

    # -- helpers -------------------------------------------------------------

    def _mask_if_enabled(self, data: Any) -> Any:
        if not self._enable_masking:
            return data
        try:
            from onyx.tracing.masking import mask_sensitive_data

            return mask_sensitive_data(data)
        except Exception as e:
            logger.warning(f"Failed to mask data: {e}")
            return data

    @staticmethod
    def _safe_str(value: Any, max_len: int = 32_000) -> str:
        """Stringify a value, truncating to *max_len* characters."""
        try:
            import json

            s = json.dumps(value, default=str, ensure_ascii=False)
        except Exception:
            s = str(value)
        if len(s) > max_len:
            s = s[:max_len] + "...[truncated]"
        return s

    def _calculate_cost(self, data: GenerationSpanData) -> Optional[float]:
        """Calculate LLM cost in dollars for this generation span."""
        try:
            from onyx.llm.cost import calculate_llm_cost_cents

            usage = data.usage or {}
            prompt_tokens = (
                usage.get("prompt_tokens") or usage.get("input_tokens") or 0
            )
            completion_tokens = (
                usage.get("completion_tokens") or usage.get("output_tokens") or 0
            )

            if data.model and prompt_tokens and completion_tokens:
                cost_cents = calculate_llm_cost_cents(
                    model_name=data.model,
                    prompt_tokens=int(prompt_tokens),
                    completion_tokens=int(completion_tokens),
                )
                if cost_cents > 0:
                    return cost_cents / 100.0
        except Exception as e:
            logger.debug(f"Failed to calculate cost: {e}")
        return None

    def _cleanup_stale_entries(self) -> None:
        """Remove tracking entries older than TTL to prevent memory leaks.

        Called periodically from on_trace_end to keep maps bounded even if
        some traces never properly close.
        """
        now = time.monotonic()
        cutoff = now - _STALE_ENTRY_TTL_SECONDS

        stale_traces = [
            tid
            for tid, ts in self._trace_timestamps.items()
            if ts < cutoff
        ]
        for tid in stale_traces:
            otel_span = self._trace_root_spans.pop(tid, None)
            if otel_span:
                try:
                    otel_span.end()
                except Exception:
                    pass
            self._first_input.pop(tid, None)
            self._last_output.pop(tid, None)
            self._trace_timestamps.pop(tid, None)

        stale_spans = [
            sid
            for sid, ts in self._span_timestamps.items()
            if ts < cutoff
        ]
        for sid in stale_spans:
            otel_span = self._otel_spans.pop(sid, None)
            if otel_span:
                try:
                    otel_span.end()
                except Exception:
                    pass
            self._span_timestamps.pop(sid, None)

        if stale_traces or stale_spans:
            logger.warning(
                f"Phoenix: cleaned up {len(stale_traces)} stale traces "
                f"and {len(stale_spans)} stale spans"
            )

    # -- TracingProcessor interface ------------------------------------------

    def on_trace_start(self, trace: Trace) -> None:
        try:
            trace_meta = trace.export() or {}
            metadata = trace_meta.get("metadata") or {}

            # Read user context from context vars (set by auth middleware)
            from shared_configs.contextvars import CURRENT_USER_EMAIL_CONTEXTVAR
            from shared_configs.contextvars import CURRENT_USER_ID_CONTEXTVAR

            user_id = CURRENT_USER_ID_CONTEXTVAR.get()
            user_email = CURRENT_USER_EMAIL_CONTEXTVAR.get()

            # Start a root span for the whole trace
            attrs: dict[str, Any] = {
                "phoenix.trace_id": trace.trace_id,
                "session.id": metadata.get("chat_session_id", ""),
                "trace.type": "root",
            }
            if user_id:
                attrs["user.id"] = user_id
            if user_email:
                attrs["user.email"] = user_email
            tenant_id = metadata.get("tenant_id")
            if tenant_id:
                attrs["tenant.id"] = tenant_id

            otel_span = self._tracer.start_span(
                name=trace.name,
                attributes=attrs,
            )

            with self._lock:
                self._trace_root_spans[trace.trace_id] = otel_span
                self._trace_timestamps[trace.trace_id] = time.monotonic()
        except Exception as e:
            logger.error(f"Error starting Phoenix trace: {e}")

    def on_trace_end(self, trace: Trace) -> None:
        try:
            with self._lock:
                otel_span = self._trace_root_spans.pop(trace.trace_id, None)
                first_input = self._first_input.pop(trace.trace_id, None)
                last_output = self._last_output.pop(trace.trace_id, None)
                self._trace_timestamps.pop(trace.trace_id, None)

                # Periodic cleanup of stale entries
                self._cleanup_stale_entries()

            if otel_span:
                if first_input is not None:
                    otel_span.set_attribute(
                        "input.value",
                        self._safe_str(self._mask_if_enabled(first_input)),
                    )
                if last_output is not None:
                    otel_span.set_attribute(
                        "output.value",
                        self._safe_str(self._mask_if_enabled(last_output)),
                    )
                otel_span.end()
        except Exception as e:
            logger.error(f"Error ending Phoenix trace: {e}")

    def on_span_start(self, span: Span[SpanData]) -> None:
        try:
            data = span.span_data

            # Determine parent context
            with self._lock:
                parent_otel = None
                if span.parent_id and span.parent_id in self._otel_spans:
                    parent_otel = self._otel_spans[span.parent_id]
                elif span.trace_id in self._trace_root_spans:
                    parent_otel = self._trace_root_spans[span.trace_id]

            # Build a context from the parent so Phoenix nests correctly
            if parent_otel:
                ctx = otel_trace.set_span_in_context(parent_otel)
            else:
                ctx = None

            # Build attributes based on span type
            attrs: dict[str, Any] = {
                "phoenix.span_id": span.span_id,
                "phoenix.trace_id": span.trace_id,
            }

            if isinstance(data, GenerationSpanData):
                span_name = f"LLM {data.model or 'unknown'}"
                attrs["openinference.span.kind"] = "LLM"
                attrs["llm.model_name"] = data.model or ""
                if data.model_config and isinstance(data.model_config, dict):
                    for k in (
                        "temperature",
                        "max_tokens",
                        "top_p",
                        "frequency_penalty",
                        "presence_penalty",
                    ):
                        if k in data.model_config:
                            attrs[f"llm.invocation_parameters.{k}"] = str(
                                data.model_config[k]
                            )
            elif isinstance(data, FunctionSpanData):
                span_name = f"Tool: {data.name}"
                attrs["openinference.span.kind"] = "TOOL"
                attrs["tool.name"] = data.name
            elif isinstance(data, AgentSpanData):
                span_name = f"Agent: {data.name}"
                attrs["openinference.span.kind"] = "AGENT"
                if data.tools:
                    attrs["agent.tools"] = ",".join(data.tools)
                if data.handoffs:
                    attrs["agent.handoffs"] = ",".join(data.handoffs)
                if data.output_type:
                    attrs["agent.output_type"] = data.output_type
            else:
                span_name = data.type if hasattr(data, "type") else "span"
                attrs["openinference.span.kind"] = "CHAIN"

            otel_span = self._tracer.start_span(
                name=span_name,
                context=ctx,
                attributes=attrs,
            )

            with self._lock:
                self._otel_spans[span.span_id] = otel_span
                self._span_timestamps[span.span_id] = time.monotonic()
        except Exception as e:
            logger.error(f"Error starting Phoenix span: {e}")

    def on_span_end(self, span: Span[SpanData]) -> None:
        try:
            with self._lock:
                otel_span = self._otel_spans.pop(span.span_id, None)
                self._span_timestamps.pop(span.span_id, None)

            if not otel_span:
                return

            data = span.span_data
            input_data: Optional[Any] = None
            output_data: Optional[Any] = None

            if isinstance(data, GenerationSpanData):
                input_data = data.input
                output_data = data.output
                if data.input is not None:
                    otel_span.set_attribute(
                        "input.value",
                        self._safe_str(self._mask_if_enabled(data.input)),
                    )
                if data.output is not None:
                    otel_span.set_attribute(
                        "output.value",
                        self._safe_str(self._mask_if_enabled(data.output)),
                    )

                # Reasoning — capture LLM chain-of-thought for audit trail
                if data.reasoning:
                    otel_span.set_attribute(
                        "llm.reasoning",
                        self._safe_str(data.reasoning),
                    )

                # Time to first action (TTFA) for latency analysis
                if data.time_to_first_action_seconds is not None:
                    otel_span.set_attribute(
                        "llm.time_to_first_action_seconds",
                        data.time_to_first_action_seconds,
                    )

                # Token usage — Phoenix reads these for cost/usage dashboards
                usage = data.usage or {}
                prompt_tokens = (
                    usage.get("prompt_tokens") or usage.get("input_tokens")
                )
                completion_tokens = (
                    usage.get("completion_tokens") or usage.get("output_tokens")
                )
                if prompt_tokens is not None:
                    otel_span.set_attribute(
                        "llm.token_count.prompt", int(prompt_tokens)
                    )
                if completion_tokens is not None:
                    otel_span.set_attribute(
                        "llm.token_count.completion", int(completion_tokens)
                    )
                total = usage.get("total_tokens")
                if total is not None:
                    otel_span.set_attribute(
                        "llm.token_count.total", int(total)
                    )
                elif prompt_tokens and completion_tokens:
                    otel_span.set_attribute(
                        "llm.token_count.total",
                        int(prompt_tokens) + int(completion_tokens),
                    )

                # Cache token details for prompt caching analysis
                cache_read = usage.get("cache_read_input_tokens")
                if cache_read is not None:
                    otel_span.set_attribute(
                        "llm.token_count.cache_read", int(cache_read)
                    )
                cache_creation = usage.get("cache_creation_input_tokens")
                if cache_creation is not None:
                    otel_span.set_attribute(
                        "llm.token_count.cache_creation", int(cache_creation)
                    )

                # Cost tracking
                cost = self._calculate_cost(data)
                if cost is not None:
                    otel_span.set_attribute("llm.cost.dollars", cost)

            elif isinstance(data, FunctionSpanData):
                input_data = data.input
                output_data = data.output
                if data.input is not None:
                    otel_span.set_attribute(
                        "input.value",
                        self._safe_str(self._mask_if_enabled(data.input)),
                    )
                if data.output is not None:
                    otel_span.set_attribute(
                        "output.value",
                        self._safe_str(self._mask_if_enabled(data.output)),
                    )

            elif isinstance(data, AgentSpanData):
                # Agent spans don't have direct input/output but we still
                # mark them as completed for the span hierarchy.
                pass

            # Record errors
            if span.error:
                otel_span.set_status(
                    StatusCode.ERROR,
                    f"{span.error.get('message')}: {span.error.get('data')}",
                )

            otel_span.end()

            # Track first input / last output per trace
            trace_id = span.trace_id
            with self._lock:
                if trace_id not in self._first_input and input_data is not None:
                    self._first_input[trace_id] = input_data
                if output_data is not None:
                    self._last_output[trace_id] = output_data

        except Exception as e:
            logger.error(f"Error ending Phoenix span: {e}")

    def force_flush(self) -> None:
        try:
            self._provider.force_flush()
        except Exception as e:
            logger.warning(f"Failed to flush Phoenix spans: {e}")

    def shutdown(self) -> None:
        try:
            self.force_flush()
            self._provider.shutdown()
        except Exception as e:
            logger.warning(f"Failed to shutdown Phoenix provider: {e}")
