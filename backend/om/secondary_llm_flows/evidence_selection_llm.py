"""Resolve the model used for the search tool's evidence selection.

Evidence selection = the two LLM steps that decide which retrieved sections reach
the answer model (`select_sections_for_expansion` over the whole list, then
`classify_section_relevance` per selected section). They are short, low-effort
calls, so a cheaper model can run them. With no config the chat model is used,
exactly as before.

Config (env, see `# --- complete-answer-prompts ---` in app_configs.py):
    EVIDENCE_SELECTION_LLM_PROVIDER  provider NAME as shown in Admin -> LLM
    EVIDENCE_SELECTION_LLM_NAME      model name, e.g. gpt-4o-mini

The configured model applies to every agent, including agents pinned to a
stronger chat model (decided 2026-10-30). Any failure falls back to the chat
model: selection must never break search.
"""

from om.configs import app_configs
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.llm import fetch_llm_provider_view
from om.llm.factory import llm_from_provider
from om.llm.interfaces import LLM
from om.utils.logger import setup_logger

logger = setup_logger()


def _configured_pair() -> tuple[str, str] | None:
    """(provider_name, model_name) when both are set; None otherwise (warns when
    only one of the two is set)."""
    provider_name = app_configs.EVIDENCE_SELECTION_LLM_PROVIDER
    model_name = app_configs.EVIDENCE_SELECTION_LLM_NAME
    if provider_name and model_name:
        return provider_name, model_name
    if provider_name or model_name:
        logger.warning(
            "Evidence selection: set both EVIDENCE_SELECTION_LLM_PROVIDER and "
            "EVIDENCE_SELECTION_LLM_NAME (only one is set); using the chat model."
        )
    return None


def resolve_evidence_selection_llm(chat_llm: LLM) -> LLM:
    """Return the LLM for evidence selection, or `chat_llm` when none is
    configured or the configured one cannot be built."""
    pair = _configured_pair()
    if pair is None:
        return chat_llm
    provider_name, model_name = pair

    try:
        with get_session_with_current_tenant() as db_session:
            provider_view = fetch_llm_provider_view(db_session, provider_name)
        if provider_view is None:
            raise ValueError(f"no LLM provider named '{provider_name}'")
        return llm_from_provider(model_name=model_name, llm_provider=provider_view)
    except Exception as e:
        logger.warning(
            f"Evidence selection: could not build '{model_name}' from provider "
            f"'{provider_name}' ({e}); using the chat model."
        )
        return chat_llm
