"""LLM-backed query expander.

Produces, from a user query (+ optional conversation history):
  * a single history-aware standalone *semantic rephrase*, and
  * keyword-only variants from a history-independent and a history-aware pass.

Every strategy call is isolated in try/except: a failure is recorded in the trace
and the flow degrades to whatever succeeded (never raising into the caller). Each
call is traced (tokens, latency, raw output, parsed variants), history is
truncated to fit a token budget, and output length is capped via ``max_tokens``.
"""

import json
import re
import time

from om.llm.factory import get_default_llm
from om.llm.interfaces import LLM
from om.llm.models import ChatCompletionMessage
from om.llm.models import ReasoningEffort
from om.llm.models import SystemMessage
from om.llm.models import UserMessage
from om.search.expansion import prompts
from om.search.expansion.config import QueryExpansionConfig
from om.search.expansion.models import ExpansionStrategy
from om.search.expansion.models import HistoryTurn
from om.search.expansion.models import QueryExpansionResult
from om.search.expansion.models import StrategyTrace
from om.search.log_events import ACTION_EXECUTE
from om.search.log_events import emit_search_event
from om.search.log_events import STATUS_SUCCESS
from om.utils.logger import setup_logger

logger = setup_logger()

# Token-budget heuristics for history-aware prompts.
_CHARS_PER_TOKEN = 4  # rough estimate to avoid a hard tokenizer dependency
_MAX_HISTORY_TURNS = 10
_RESERVED_TOKENS = 1024  # prompt template + output headroom
_OUTPUT_MAX_TOKENS = 512  # cap on expansion output
_DEFAULT_MAX_INPUT_TOKENS = 8000
_MIN_HISTORY_CHARS = 500


class QueryExpander:
    """Service that turns a query into expanded/rephrased retrieval variants."""

    def __init__(
        self, config: QueryExpansionConfig, llm: LLM | None = None
    ) -> None:
        self._config = config
        self._llm = llm

    @property
    def llm(self) -> LLM:
        # Lazily constructed so a disabled/failed flow never pays for it.
        if self._llm is None:
            self._llm = get_default_llm(temperature=0.0)
        return self._llm

    # -- public API ----------------------------------------------------------

    def expand(
        self, query: str, history: list[HistoryTurn] | None = None
    ) -> QueryExpansionResult:
        history = history or []
        result = QueryExpansionResult(original_query=query)
        cfg = self._config
        if not cfg.enable_expansion or not query.strip():
            return result

        started = time.monotonic()
        try:
            result.trace.llm_model = self.llm.config.model_name
        except Exception:
            # LLM unavailable (e.g. no provider configured): degrade to original.
            logger.warning("query expansion LLM unavailable; returning original query")
            return result

        # 1. History-aware semantic rephrase -> single standalone question.
        if cfg.enable_semantic_rephrase and history:
            rephrase, trace = self._semantic_rephrase(query, history)
            result.trace.add(trace)
            if rephrase and rephrase.strip().lower() != query.strip().lower():
                result.rephrased_query = rephrase

        # 2. Keyword expansion (history-independent).
        seen: set[str] = {query.strip().lower()}
        if cfg.enable_keyword_expansion:
            variants, trace = self._keyword_expand(query)
            result.trace.add(trace)
            self._merge_unique(variants, result.keyword_variants, seen)

        # 3. History-aware keyword expansion.
        if cfg.enable_keyword_history_expansion and history:
            variants, trace = self._keyword_history_expand(query, history)
            result.trace.add(trace)
            self._merge_unique(variants, result.keyword_variants, seen)

        result.trace.total_duration_ms = (time.monotonic() - started) * 1000.0

        emit_search_event(
            event="search.expanded",
            action=ACTION_EXECUTE,
            status=STATUS_SUCCESS,
            duration_ms=result.trace.total_duration_ms,
            num_keyword_variants=len(result.keyword_variants),
            has_rephrase=result.rephrased_query is not None,
            llm_model=result.trace.llm_model,
            total_prompt_tokens=result.trace.total_prompt_tokens,
            total_completion_tokens=result.trace.total_completion_tokens,
        )
        return result

    # -- strategies ----------------------------------------------------------

    def _semantic_rephrase(
        self, query: str, history: list[HistoryTurn]
    ) -> tuple[str | None, StrategyTrace]:
        trace = StrategyTrace(
            strategy=ExpansionStrategy.SEMANTIC_REPHRASE, status="skipped"
        )
        try:
            turns, truncated = self._prepare_history(history)
            trace.truncated_history = truncated
            user_prompt = prompts.SEMANTIC_REPHRASE_USER.format(
                history=prompts.format_history(turns), query=query
            )
            content = self._invoke(
                prompts.SEMANTIC_REPHRASE_SYSTEM, user_prompt, trace
            )
            rephrase = self._clean_single_line(content)
            trace.variants = [rephrase] if rephrase else []
            trace.status = "success" if rephrase else "error"
            return (rephrase or None), trace
        except Exception as exc:
            trace.status = "error"
            trace.error = f"{type(exc).__name__}: {exc}"
            logger.warning("semantic rephrase failed: %s", exc)
            return None, trace

    def _keyword_expand(self, query: str) -> tuple[list[str], StrategyTrace]:
        trace = StrategyTrace(strategy=ExpansionStrategy.KEYWORD, status="skipped")
        try:
            user_prompt = prompts.KEYWORD_EXPANSION_USER.format(
                query=query, max_variants=self._config.max_variants
            )
            content = self._invoke(
                prompts.KEYWORD_EXPANSION_SYSTEM, user_prompt, trace
            )
            variants = self._parse_json_list(content, self._config.max_variants)
            trace.variants = variants
            trace.status = "success" if variants else "error"
            return variants, trace
        except Exception as exc:
            trace.status = "error"
            trace.error = f"{type(exc).__name__}: {exc}"
            logger.warning("keyword expansion failed: %s", exc)
            return [], trace

    def _keyword_history_expand(
        self, query: str, history: list[HistoryTurn]
    ) -> tuple[list[str], StrategyTrace]:
        trace = StrategyTrace(
            strategy=ExpansionStrategy.KEYWORD_HISTORY, status="skipped"
        )
        try:
            turns, truncated = self._prepare_history(history)
            trace.truncated_history = truncated
            user_prompt = prompts.KEYWORD_HISTORY_USER.format(
                history=prompts.format_history(turns),
                query=query,
                max_variants=self._config.max_variants,
            )
            content = self._invoke(
                prompts.KEYWORD_HISTORY_SYSTEM, user_prompt, trace
            )
            variants = self._parse_json_list(content, self._config.max_variants)
            trace.variants = variants
            trace.status = "success" if variants else "error"
            return variants, trace
        except Exception as exc:
            trace.status = "error"
            trace.error = f"{type(exc).__name__}: {exc}"
            logger.warning("keyword-history expansion failed: %s", exc)
            return [], trace

    # -- LLM plumbing --------------------------------------------------------

    def _invoke(
        self, system_prompt: str, user_prompt: str, trace: StrategyTrace
    ) -> str:
        messages: list[ChatCompletionMessage] = [
            SystemMessage(content=system_prompt),
            UserMessage(content=user_prompt),
        ]
        started = time.monotonic()
        response = self.llm.invoke(
            messages,
            max_tokens=_OUTPUT_MAX_TOKENS,
            reasoning_effort=ReasoningEffort.LOW,
        )
        trace.duration_ms = (time.monotonic() - started) * 1000.0
        if response.usage is not None:
            trace.prompt_tokens = response.usage.prompt_tokens
            trace.completion_tokens = response.usage.completion_tokens
        content = (response.choice.message.content or "").strip()
        trace.raw_output = content
        return content

    # -- history token budget ------------------------------------------------

    def _char_budget(self) -> int:
        try:
            max_input = self.llm.config.max_input_tokens or _DEFAULT_MAX_INPUT_TOKENS
        except Exception:
            max_input = _DEFAULT_MAX_INPUT_TOKENS
        usable = max_input - _RESERVED_TOKENS - _OUTPUT_MAX_TOKENS
        return max(_MIN_HISTORY_CHARS, usable * _CHARS_PER_TOKEN)

    def _prepare_history(
        self, history: list[HistoryTurn]
    ) -> tuple[list[tuple[str, str]], bool]:
        """Return the most recent turns that fit the char budget, newest kept.

        Returns (turns_oldest_first, truncated).
        """
        truncated = False
        recent = history[-_MAX_HISTORY_TURNS:]
        if len(recent) < len(history):
            truncated = True

        budget = self._char_budget()
        kept: list[HistoryTurn] = []
        total = 0
        # Walk newest -> oldest, keeping turns until the budget is exhausted.
        for turn in reversed(recent):
            cost = len(turn.content) + len(turn.role) + 2
            if total + cost > budget and kept:
                truncated = True
                break
            kept.append(turn)
            total += cost
        kept.reverse()
        return [(t.role, t.content) for t in kept], truncated

    # -- parsing helpers -----------------------------------------------------

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```[a-zA-Z0-9]*\s*\n?", "", stripped)
            stripped = re.sub(r"\n?```\s*$", "", stripped)
        return stripped.strip()

    def _parse_json_list(self, text: str, cap: int) -> list[str]:
        if not text:
            return []
        cleaned = self._strip_code_fences(text)
        raw_items: list[str] = []

        start, end = cleaned.find("["), cleaned.rfind("]")
        parsed = None
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(cleaned[start : end + 1])
            except Exception:
                parsed = None

        if isinstance(parsed, list):
            for element in parsed:
                if isinstance(element, str):
                    raw_items.append(element)
                elif isinstance(element, dict):
                    for key in ("query", "text", "keywords"):
                        value = element.get(key)
                        if isinstance(value, str):
                            raw_items.append(value)
                            break
        else:
            # Fallback: treat each line as a variant, stripping list markers.
            for line in cleaned.splitlines():
                candidate = re.sub(r"^[-*\d.)\s\"']+", "", line.strip())
                if candidate:
                    raw_items.append(candidate)

        out: list[str] = []
        seen: set[str] = set()
        for item in raw_items:
            value = item.strip().strip("\"'").strip()
            key = value.lower()
            if value and key not in seen:
                seen.add(key)
                out.append(value)
            if len(out) >= cap:
                break
        return out

    @staticmethod
    def _clean_single_line(text: str) -> str:
        for line in text.splitlines():
            candidate = line.strip().strip("\"'").strip()
            if candidate:
                return candidate
        return ""

    @staticmethod
    def _merge_unique(
        source: list[str], target: list[str], seen: set[str]
    ) -> None:
        for value in source:
            key = value.strip().lower()
            if key and key not in seen:
                seen.add(key)
                target.append(value.strip())
