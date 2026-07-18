# VirtualAI Web Crawler — Implementation Reference

This document is the single source of truth for the enhanced web crawler.
Use it to resume work if context is lost.

## Architecture Overview

```
Chat question → web_search tool (finds URLs) → open_url tool → WebContentProvider.contents(urls) → LLM
                                                                    ↑
                                                        VirtualAIWebCrawler (NEW)
                                                        replaces OnyxWebCrawler
```

## What Changed

**Old:** `OnyxWebCrawler` — simple HTTP with bot user-agent, no retry, no JS fallback, sequential.
**New:** `VirtualAIWebCrawler` — realistic Chrome headers, retry, parallel fetch, Playwright fallback, trafilatura.

## Files Modified

| File | Change |
|------|--------|
| `backend/om/tools/tool_implementations/open_url/virtualai_web_crawler.py` | **NEW** — robust crawler class |
| `backend/om/tools/tool_implementations/open_url/onyx_web_crawler.py` | **UNCHANGED** — kept as-is for backward compat |
| `backend/om/tools/tool_implementations/web_search/providers.py` | Updated imports: `OnyxWebCrawler` → `VirtualAIWebCrawler` |
| `backend/om/server/features/web_search/api.py` | Updated imports: `OnyxWebCrawler` → `VirtualAIWebCrawler` |
| `backend/om/file_processing/html_utils.py` | Added `extract_published_date()` helper |
| `backend/shared_configs/enums.py` | `WebContentProviderType` unchanged — still uses `ONYX_WEB_CRAWLER` enum value |

## VirtualAIWebCrawler Design

```python
class VirtualAIWebCrawler(WebContentProvider):
    """Drop-in replacement for OnyxWebCrawler with robust fetching."""

    def contents(self, urls: Sequence[str]) -> list[WebContent]:
        # Phase 1: Parallel HTTP fetch with realistic Chrome headers
        #          ThreadPoolExecutor, max 5 workers
        #          Smart retry: only retries on transient errors (network, 403, 429, 5xx)
        #          Skips retry for non-retryable errors (404, 401, SSRF block)
        #
        # Phase 2: Collect failed URLs (empty, "Loading...", <50 chars)
        #
        # Phase 3: Playwright fallback for failed URLs
        #          Reuses start_playwright() from connector.py
        #          Single shared browser context, closed after batch
        #
        # Phase 4: Return merged results
```

### Key Imports Reused (No Duplication)

| What | From |
|------|------|
| `DEFAULT_HEADERS`, `DEFAULT_USER_AGENT` | `onyx.connectors.web.connector` |
| `start_playwright()`, `BOT_DETECTION_GRACE_PERIOD_MS` | `onyx.connectors.web.connector` |
| `web_html_cleanup()`, `parse_html_with_trafilatura()` | `onyx.file_processing.html_utils` |
| `ssrf_safe_get()`, `SSRFException` | `onyx.utils.url` |
| `decode_html_bytes()`, `extract_pdf_text()`, `is_pdf_resource()` | `onyx.utils.web_content` |
| `WebContent`, `WebContentProvider` | `onyx.tools.tool_implementations.open_url.models` |

### Reference Points in providers.py

Three places instantiate the crawler (all updated to VirtualAIWebCrawler):

1. `build_content_provider_from_config()` line ~151 — when `ONYX_WEB_CRAWLER` type selected
2. `get_default_content_provider()` line ~202 — fallback when no provider configured
3. In `api.py` `_get_active_content_provider()` line ~106 — API endpoint fallback

### Reference Points in api.py

Imports from onyx_web_crawler.py:
- `DEFAULT_MAX_HTML_SIZE_BYTES` (line 23)
- `DEFAULT_MAX_PDF_SIZE_BYTES` (line 26)
- `OnyxWebCrawler` (line 29) → changed to VirtualAIWebCrawler

## E2E Test Script

`backend/tests/web_crawler/test_crawler.py` — standalone test that:

1. Instantiates VirtualAIWebCrawler directly (no server needed)
2. Tests against real news sites:
   - example.com (baseline)
   - thehindu.com (Indian news)
   - bbc.com (international)
   - eenadu.net (Telugu)
   - ndtv.com (CDN-protected, tests Playwright fallback)
3. Verifies: content length > 50 chars, title extracted, scrape_successful=True
4. Run: `python -m pytest backend/tests/web_crawler/test_crawler.py -v`
   Or standalone: `python backend/tests/web_crawler/test_crawler.py`

## Configuration (Environment Variables)

No new env vars. Existing ones apply:
- `WEB_CONNECTOR_VALIDATE_URLS` — SSRF validation
- `WEB_CONNECTOR_IGNORED_CLASSES` — CSS classes to strip (default: sidebar,footer)
- `WEB_CONNECTOR_IGNORED_ELEMENTS` — HTML elements to strip

## Enum Note

`shared_configs/enums.py` `WebContentProviderType.ONYX_WEB_CRAWLER = "onyx_web_crawler"` is NOT changed.
The enum value stays the same — only the underlying class implementation changes.
This means the database, frontend, and API all continue working without any migration.
