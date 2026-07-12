import requests
from fastapi import HTTPException

from om.tools.tool_implementations.web_search.models import (
    WebSearchProvider,
)
from om.tools.tool_implementations.web_search.models import (
    WebSearchResult,
)
from om.utils.logger import setup_logger
from om.utils.retry_wrapper import retry_builder

logger = setup_logger()

# Default Perplexica provider/model config — can be overridden via admin config
DEFAULT_CHAT_MODEL_KEY = "gpt-4o-mini"
DEFAULT_EMBEDDING_MODEL_KEY = "Xenova/all-MiniLM-L6-v2"
DEFAULT_OPTIMIZATION_MODE = "speed"
DEFAULT_SOURCES = ["web"]


class SmartSearchClient(WebSearchProvider):
    """Web search provider backed by SmartSearch AI (Perplexica).

    Calls Perplexica's POST /api/search endpoint, which:
    1. Classifies and rewrites the query
    2. Runs web research via SearxNG
    3. Returns AI-synthesized answer + cited sources

    We extract the sources as WebSearchResult objects, fitting the
    same pattern as Google PSE, Brave, SearXNG, etc.
    """

    def __init__(
        self,
        base_url: str,
        num_results: int = 10,
        chat_model_provider_id: str | None = None,
        chat_model_key: str = DEFAULT_CHAT_MODEL_KEY,
        embedding_model_provider_id: str | None = None,
        embedding_model_key: str = DEFAULT_EMBEDDING_MODEL_KEY,
        optimization_mode: str = DEFAULT_OPTIMIZATION_MODE,
        sources: list[str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._num_results = num_results
        self._chat_model_key = chat_model_key
        self._embedding_model_key = embedding_model_key
        self._optimization_mode = optimization_mode
        self._sources = sources or DEFAULT_SOURCES

        # Provider IDs are auto-discovered if not provided
        self._chat_model_provider_id = chat_model_provider_id
        self._embedding_model_provider_id = embedding_model_provider_id

    def _discover_provider_ids(self) -> None:
        """Auto-discover provider IDs from Perplexica if not configured."""
        if self._chat_model_provider_id and self._embedding_model_provider_id:
            return

        try:
            resp = requests.get(
                f"{self._base_url}/api/providers", timeout=10
            )
            resp.raise_for_status()
            providers = resp.json().get("providers", [])
        except Exception as e:
            logger.warning(f"SmartSearch: Could not discover providers: {e}")
            return

        for provider in providers:
            models = provider.get("chatModels", [])
            embeddings = provider.get("embeddingModels", [])

            if not self._chat_model_provider_id:
                for m in models:
                    if m.get("key") == self._chat_model_key:
                        self._chat_model_provider_id = provider["id"]
                        break

            if not self._embedding_model_provider_id:
                for m in embeddings:
                    if m.get("key") == self._embedding_model_key:
                        self._embedding_model_provider_id = provider["id"]
                        break

        if not self._chat_model_provider_id:
            logger.warning(
                f"SmartSearch: Chat model '{self._chat_model_key}' not found "
                f"in any provider. Search may fail."
            )
        if not self._embedding_model_provider_id:
            logger.warning(
                f"SmartSearch: Embedding model '{self._embedding_model_key}' "
                f"not found in any provider. Search may fail."
            )

    @retry_builder(tries=2, delay=2, backoff=2)
    def search(self, query: str) -> list[WebSearchResult]:
        self._discover_provider_ids()

        payload = {
            "query": query,
            "sources": self._sources,
            "optimizationMode": self._optimization_mode,
            "stream": False,
            "history": [],
            "chatModel": {
                "providerId": self._chat_model_provider_id or "",
                "key": self._chat_model_key,
            },
            "embeddingModel": {
                "providerId": self._embedding_model_provider_id or "",
                "key": self._embedding_model_key,
            },
        }

        logger.debug(
            f"SmartSearch: Searching for '{query}' at {self._base_url}/api/search"
        )

        response = requests.post(
            f"{self._base_url}/api/search",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()

        data = response.json()
        sources = data.get("sources", [])

        results: list[WebSearchResult] = []
        for source in sources[: self._num_results]:
            metadata = source.get("metadata", {})
            title = metadata.get("title", "")
            url = metadata.get("url", "")
            content = source.get("content", "")

            if url:
                results.append(
                    WebSearchResult(
                        title=title or "Untitled",
                        link=url,
                        snippet=content[:500] if content else "",
                    )
                )

        logger.info(
            f"SmartSearch: Found {len(results)} results for '{query[:50]}...'"
        )
        return results

    def test_connection(self) -> dict[str, str]:
        try:
            resp = requests.get(
                f"{self._base_url}/api/providers", timeout=10
            )
            resp.raise_for_status()
        except requests.ConnectionError as e:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Could not connect to SmartSearch AI at {self._base_url}. "
                    f"Please check the URL and ensure Perplexica is running."
                ),
            ) from e
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            raise HTTPException(
                status_code=400,
                detail=(
                    f"SmartSearch AI connection failed "
                    f"(status {status_code}): {str(e)}"
                ),
            ) from e

        providers = resp.json().get("providers", [])
        if not providers:
            raise HTTPException(
                status_code=400,
                detail=(
                    "SmartSearch AI is reachable but has no providers configured. "
                    "Please configure at least one LLM provider in Perplexica."
                ),
            )

        # Auto-discover and validate model availability
        self._discover_provider_ids()

        # Run a quick test search
        try:
            results = self.search("test")
            logger.info(
                f"SmartSearch: Test search returned {len(results)} results."
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"SmartSearch AI test search failed: {str(e)}",
            ) from e

        logger.info("Web search provider test succeeded for SmartSearch AI.")
        return {"status": "ok"}
