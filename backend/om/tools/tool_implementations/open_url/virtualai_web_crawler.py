from __future__ import annotations

import json
import random
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from datetime import timezone

from om.connectors.web.connector import BOT_DETECTION_GRACE_PERIOD_MS
from om.connectors.web.connector import DEFAULT_HEADERS
from om.connectors.web.connector import DEFAULT_USER_AGENT
from om.file_processing.html_utils import parse_html_with_trafilatura
from om.file_processing.html_utils import ParsedHTML
from om.file_processing.html_utils import web_html_cleanup
from om.tools.tool_implementations.open_url.models import WebContent
from om.tools.tool_implementations.open_url.models import WebContentProvider
from om.utils.logger import setup_logger
from om.utils.url import ssrf_safe_get
from om.utils.url import SSRFException
from om.utils.web_content import decode_html_bytes
from om.utils.web_content import extract_pdf_text
from om.utils.web_content import is_pdf_resource
from om.utils.web_content import title_from_pdf_metadata
from om.utils.web_content import title_from_url

logger = setup_logger()

# ── Defaults ─────────────────────────────────────────────────────────────────
CRAWLER_TIMEOUT_SECONDS = 20
CRAWLER_MAX_RETRIES = 2
CRAWLER_MAX_WORKERS = 5
PLAYWRIGHT_PAGE_TIMEOUT_MS = 15000
MIN_CONTENT_LENGTH = 50

DEFAULT_MAX_PDF_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
DEFAULT_MAX_HTML_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

# HTTP status codes worth retrying (transient or rate-limit errors)
RETRYABLE_STATUS_CODES = frozenset({403, 429, 500, 502, 503, 504})

# Content patterns that indicate the page didn't load properly
INSUFFICIENT_PATTERNS = frozenset({"loading...", "just a moment...", "please wait..."})


def _is_insufficient(text: str) -> bool:
    """Check if scraped content is too short or a placeholder."""
    stripped = text.strip()
    if not stripped or len(stripped) < MIN_CONTENT_LENGTH:
        return True
    return stripped.lower() in INSUFFICIENT_PATTERNS


def _extract_published_date(html: str) -> datetime | None:
    """Extract article publication date from HTML meta tags and JSON-LD."""
    from bs4 import BeautifulSoup

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return None

    # 1. Open Graph: <meta property="article:published_time" content="...">
    og_tag = soup.find("meta", attrs={"property": "article:published_time"})
    if og_tag and og_tag.get("content"):
        dt = _parse_datetime(og_tag["content"])
        if dt:
            return dt

    # 2. <meta name="date" content="...">
    date_tag = soup.find("meta", attrs={"name": "date"})
    if date_tag and date_tag.get("content"):
        dt = _parse_datetime(date_tag["content"])
        if dt:
            return dt

    # 3. <time datetime="..."> (first one found)
    time_tag = soup.find("time", attrs={"datetime": True})
    if time_tag:
        dt = _parse_datetime(time_tag["datetime"])
        if dt:
            return dt

    # 4. JSON-LD: {"datePublished": "..."}
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = data[0] if data else {}
            date_str = data.get("datePublished") or data.get("dateCreated")
            if date_str:
                dt = _parse_datetime(date_str)
                if dt:
                    return dt
        except (json.JSONDecodeError, TypeError, IndexError):
            continue

    return None


def _parse_datetime(value: str) -> datetime | None:
    """Try multiple ISO-like formats."""
    from dateutil import parser as dateutil_parser

    try:
        dt = dateutil_parser.parse(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError, OverflowError):
        return None


class VirtualAIWebCrawler(WebContentProvider):
    """
    Robust built-in web crawler for the chat web-search tool.

    Improvements over OnyxWebCrawler:
    - Realistic Chrome browser headers (not bot user-agent)
    - Retry with exponential backoff (up to 2 retries)
    - Parallel URL fetching (ThreadPoolExecutor, max 5 workers)
    - Playwright fallback for JS-heavy / CDN-protected sites
    - Trafilatura-first content extraction for better article parsing
    - Published date extraction from HTML meta tags / JSON-LD
    """

    def __init__(
        self,
        *,
        timeout_seconds: int = CRAWLER_TIMEOUT_SECONDS,
        max_retries: int = CRAWLER_MAX_RETRIES,
        max_workers: int = CRAWLER_MAX_WORKERS,
        max_pdf_size_bytes: int | None = None,
        max_html_size_bytes: int | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._max_workers = max_workers
        self._max_pdf_size_bytes = max_pdf_size_bytes
        self._max_html_size_bytes = max_html_size_bytes
        # Use realistic Chrome headers from the web connector
        self._headers = dict(DEFAULT_HEADERS)

    # ── Public Interface ─────────────────────────────────────────────────────

    def contents(self, urls: Sequence[str]) -> list[WebContent]:
        if not urls:
            return []

        # Phase 1: Parallel HTTP fetch
        workers = min(self._max_workers, len(urls))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(self._fetch_with_retry, urls))

        # Phase 2: Identify URLs that need Playwright fallback
        failed_indices = [
            i
            for i, r in enumerate(results)
            if not r.scrape_successful or _is_insufficient(r.full_content)
        ]

        if failed_indices:
            failed_urls = [urls[i] for i in failed_indices]
            logger.info(
                "VirtualAI crawler: %d/%d URLs need Playwright fallback: %s",
                len(failed_urls),
                len(urls),
                [u[:80] for u in failed_urls],
            )
            # Phase 3: Playwright fallback
            playwright_results = self._playwright_fetch_batch(failed_urls)
            for idx, pw_result in zip(failed_indices, playwright_results):
                if pw_result.scrape_successful and not _is_insufficient(
                    pw_result.full_content
                ):
                    results[idx] = pw_result

        return results

    # ── HTTP Fetch with Retry ────────────────────────────────────────────────

    def _fetch_with_retry(self, url: str) -> WebContent:
        """Fetch a URL with retry and exponential backoff.

        Only retries on transient/retryable failures (network errors, 403, 429, 5xx).
        Non-retryable failures (404, 401, SSRF block) return immediately.
        """
        last_result: WebContent | None = None

        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                delay = min(2**attempt + random.uniform(0, 1), 8)
                logger.info(
                    "VirtualAI crawler: retry %d/%d for %s (%.1fs delay)",
                    attempt,
                    self._max_retries,
                    url[:80],
                    delay,
                )
                time.sleep(delay)

            result, retryable = self._fetch_url_http(url)

            # Success — content looks good
            if result.scrape_successful and not _is_insufficient(result.full_content):
                return result

            last_result = result

            # Don't retry non-retryable errors (404, 401, SSRF block, etc.)
            if not retryable:
                break

        # Return last attempt (will be picked up by Playwright fallback if needed)
        return last_result or self._empty_result(url)

    def _fetch_url_http(self, url: str) -> tuple[WebContent, bool]:
        """Single HTTP fetch attempt with realistic headers.

        Returns (WebContent, retryable) where retryable indicates whether
        a retry might succeed (True for network errors, 403/429/5xx;
        False for 404, 401, SSRF blocks).
        """
        try:
            response = ssrf_safe_get(
                url, headers=self._headers, timeout=self._timeout_seconds
            )
        except SSRFException as exc:
            logger.error("SSRF blocked %s: %s", url, exc)
            return self._empty_result(url), False
        except Exception as exc:
            # Network errors (timeout, DNS, connection reset) are retryable
            logger.warning(
                "VirtualAI crawler failed to fetch %s (%s)", url, exc.__class__.__name__
            )
            return self._empty_result(url), True

        if response.status_code >= 400:
            retryable = response.status_code in RETRYABLE_STATUS_CODES
            logger.warning(
                "VirtualAI crawler received HTTP %s for %s (%s)",
                response.status_code,
                url,
                "will retry" if retryable else "not retryable",
            )
            return self._empty_result(url), retryable

        content_type = response.headers.get("Content-Type", "")
        content_sniff = response.content[:1024] if response.content else None

        # Handle PDF
        if is_pdf_resource(url, content_type, content_sniff):
            return self._handle_pdf(url, response.content), False

        # Handle HTML
        if (
            self._max_html_size_bytes is not None
            and len(response.content) > self._max_html_size_bytes
        ):
            logger.warning(
                "HTML too large (%d bytes) for %s", len(response.content), url
            )
            return self._empty_result(url), False

        result = self._parse_html_response(
            url,
            response.content,
            content_type,
            response.apparent_encoding or response.encoding,
        )
        # If we got a 200 but content is insufficient (JS-rendered page),
        # it's worth retrying (might get different response) or falling back to Playwright
        retryable = not result.scrape_successful or _is_insufficient(
            result.full_content
        )
        return result, retryable

    # ── Playwright Fallback ──────────────────────────────────────────────────

    def _playwright_fetch_batch(self, urls: list[str]) -> list[WebContent]:
        """Fetch multiple URLs using Playwright headless browser."""
        results: list[WebContent] = []

        try:
            from om.connectors.web.connector import start_playwright

            playwright, context = start_playwright()
        except Exception as exc:
            logger.warning(
                "VirtualAI crawler: Playwright init failed (%s), skipping fallback",
                exc.__class__.__name__,
            )
            return [self._empty_result(u) for u in urls]

        try:
            for url in urls:
                result = self._playwright_fetch_single(url, context)
                results.append(result)
        finally:
            try:
                context.close()
                playwright.stop()
            except Exception:
                pass

        return results

    def _playwright_fetch_single(self, url: str, context: object) -> WebContent:
        """Fetch a single URL using an existing Playwright browser context."""
        from playwright.sync_api import BrowserContext

        if not isinstance(context, BrowserContext):
            return self._empty_result(url)

        page = context.new_page()
        try:
            page_response = page.goto(
                url,
                timeout=PLAYWRIGHT_PAGE_TIMEOUT_MS,
                wait_until="commit",
            )
            # Grace period for bot detection / JS rendering
            page.wait_for_timeout(BOT_DETECTION_GRACE_PERIOD_MS)

            if page_response and page_response.status >= 400:
                logger.warning(
                    "VirtualAI crawler (Playwright) HTTP %s for %s",
                    page_response.status,
                    url,
                )
                return self._empty_result(url)

            html_content = page.content()
            return self._parse_html_string(url, html_content)
        except Exception as exc:
            logger.warning(
                "VirtualAI crawler (Playwright) failed for %s: %s",
                url,
                exc.__class__.__name__,
            )
            return self._empty_result(url)
        finally:
            page.close()

    # ── Content Parsing ──────────────────────────────────────────────────────

    def _parse_html_response(
        self,
        url: str,
        content_bytes: bytes,
        content_type: str,
        fallback_encoding: str | None,
    ) -> WebContent:
        """Parse HTML bytes into WebContent."""
        try:
            decoded_html = decode_html_bytes(
                content_bytes,
                content_type=content_type,
                fallback_encoding=fallback_encoding,
            )
            return self._parse_html_string(url, decoded_html)
        except Exception as exc:
            logger.warning(
                "VirtualAI crawler failed to parse %s (%s)", url, exc.__class__.__name__
            )
            return self._empty_result(url)

    def _parse_html_string(self, url: str, html: str) -> WebContent:
        """Parse an HTML string into WebContent using trafilatura-first strategy."""
        title = ""
        text_content = ""

        try:
            # Extract title via BeautifulSoup (fast, reliable)
            parsed: ParsedHTML = web_html_cleanup(html)
            title = (parsed.title or "").strip()

            # Try trafilatura first for better article extraction
            try:
                trafilatura_text = parse_html_with_trafilatura(html)
                if trafilatura_text and len(trafilatura_text.strip()) >= MIN_CONTENT_LENGTH:
                    text_content = trafilatura_text
            except Exception:
                pass

            # Fall back to BeautifulSoup if trafilatura returned nothing useful
            if not text_content or len(text_content.strip()) < MIN_CONTENT_LENGTH:
                text_content = parsed.cleaned_text or ""

        except Exception as exc:
            logger.warning(
                "VirtualAI crawler parse error for %s (%s)", url, exc.__class__.__name__
            )

        # Extract published date
        published_date = _extract_published_date(html)

        return WebContent(
            title=title,
            link=url,
            full_content=text_content,
            published_date=published_date,
            scrape_successful=bool(text_content.strip()),
        )

    # ── PDF Handling ─────────────────────────────────────────────────────────

    def _handle_pdf(self, url: str, content: bytes) -> WebContent:
        if (
            self._max_pdf_size_bytes is not None
            and len(content) > self._max_pdf_size_bytes
        ):
            logger.warning("PDF too large (%d bytes) for %s", len(content), url)
            return self._empty_result(url)

        try:
            text_content, metadata = extract_pdf_text(content)
            title = title_from_pdf_metadata(metadata) or title_from_url(url)
            return WebContent(
                title=title,
                link=url,
                full_content=text_content,
                published_date=None,
                scrape_successful=bool(text_content.strip()),
            )
        except Exception as exc:
            logger.warning(
                "VirtualAI crawler PDF extraction failed for %s (%s)",
                url,
                exc.__class__.__name__,
            )
            return self._empty_result(url)

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _empty_result(url: str) -> WebContent:
        return WebContent(
            title="",
            link=url,
            full_content="",
            published_date=None,
            scrape_successful=False,
        )
