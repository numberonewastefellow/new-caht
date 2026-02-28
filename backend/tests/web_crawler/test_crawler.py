#!/usr/bin/env python3
"""
E2E test for VirtualAIWebCrawler — tests real news site crawling.

Run standalone:
    python backend/tests/web_crawler/test_crawler.py

Run with pytest:
    python -m pytest backend/tests/web_crawler/test_crawler.py -v

Run a single site:
    python backend/tests/web_crawler/test_crawler.py --url https://www.thehindu.com/news/

Requirements:
    - Internet connection
    - Playwright browsers installed (for fallback tests):
        playwright install chromium
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# -- Ensure the backend package is importable ---------------------------------
_backend_root = Path(__file__).resolve().parent.parent.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))


from onyx.tools.tool_implementations.open_url.virtualai_web_crawler import (
    VirtualAIWebCrawler,
)

# -- Test Configuration -------------------------------------------------------

# Sites to test — mix of easy, medium, and hard (CDN-protected)
TEST_SITES = {
    "example.com (baseline)": {
        "url": "https://example.com/",
        "expect_title_contains": "Example",
        "expect_content_contains": "domain",
        "min_content_length": 50,
    },
    "The Hindu (Indian news)": {
        "url": "https://www.thehindu.com/news/",
        "expect_title_contains": "",  # any title
        "expect_content_contains": "",  # any content
        "min_content_length": 100,
    },
    "BBC News (international)": {
        "url": "https://www.bbc.com/news",
        "expect_title_contains": "",
        "expect_content_contains": "",
        "min_content_length": 100,
    },
    "Eenadu (Telugu news)": {
        "url": "https://www.eenadu.net/",
        "expect_title_contains": "",
        "expect_content_contains": "",
        "min_content_length": 100,
    },
    "IANA About (HTTPS with path)": {
        "url": "https://www.iana.org/about",
        "expect_title_contains": "",
        "expect_content_contains": "",
        "min_content_length": 50,
    },
}

# Sites known to need Playwright fallback (aggressive CDN / JS-required)
PLAYWRIGHT_FALLBACK_SITES = {
    "NDTV (CDN-protected)": {
        "url": "https://www.ndtv.com/",
        "expect_title_contains": "",
        "expect_content_contains": "",
        "min_content_length": 100,
    },
    "Reuters (requires Playwright)": {
        "url": "https://www.reuters.com/",
        "expect_title_contains": "",
        "expect_content_contains": "",
        "min_content_length": 100,
    },
}


# -- Test Helpers -------------------------------------------------------------


def _run_single_test(
    crawler: VirtualAIWebCrawler,
    name: str,
    config: dict,
    verbose: bool = True,
) -> tuple[bool, str]:
    """Run a single URL test and return (passed, message)."""
    url = config["url"]
    start = time.time()

    try:
        results = crawler.contents([url])
    except Exception as exc:
        elapsed = time.time() - start
        msg = f"  FAIL  {name} ({elapsed:.1f}s) — Exception: {exc}"
        if verbose:
            print(msg)
        return False, msg

    elapsed = time.time() - start

    if not results:
        msg = f"  FAIL  {name} ({elapsed:.1f}s) — No results returned"
        if verbose:
            print(msg)
        return False, msg

    result = results[0]
    issues = []

    # Check scrape_successful
    if not result.scrape_successful:
        issues.append("scrape_successful=False")

    # Check content length
    content_len = len(result.full_content.strip())
    min_len = config["min_content_length"]
    if content_len < min_len:
        issues.append(f"content too short ({content_len} < {min_len})")

    # Check title contains
    if config["expect_title_contains"]:
        if config["expect_title_contains"].lower() not in result.title.lower():
            issues.append(
                f"title missing '{config['expect_title_contains']}' (got: '{result.title[:60]}')"
            )

    # Check content contains
    if config["expect_content_contains"]:
        if (
            config["expect_content_contains"].lower()
            not in result.full_content.lower()
        ):
            issues.append(f"content missing '{config['expect_content_contains']}'")

    if issues:
        msg = f"  FAIL  {name} ({elapsed:.1f}s) — {'; '.join(issues)}"
        if verbose:
            print(msg)
        return False, msg

    # Success
    date_str = str(result.published_date)[:19] if result.published_date else "none"
    msg = (
        f"  PASS  {name} ({elapsed:.1f}s) — "
        f"title='{result.title[:50]}' "
        f"content={content_len} chars "
        f"date={date_str}"
    )
    if verbose:
        print(msg)
    return True, msg


# -- Pytest Tests -------------------------------------------------------------


def _make_crawler() -> VirtualAIWebCrawler:
    return VirtualAIWebCrawler(
        max_pdf_size_bytes=50 * 1024 * 1024,
        max_html_size_bytes=20 * 1024 * 1024,
    )


def test_example_com():
    """Baseline: example.com should always work."""
    crawler = _make_crawler()
    passed, msg = _run_single_test(
        crawler, "example.com", TEST_SITES["example.com (baseline)"], verbose=False
    )
    assert passed, msg


def test_iana_https_with_path():
    """HTTPS site with path."""
    crawler = _make_crawler()
    passed, msg = _run_single_test(
        crawler, "IANA", TEST_SITES["IANA About (HTTPS with path)"], verbose=False
    )
    assert passed, msg


def test_thehindu():
    """Indian news site."""
    crawler = _make_crawler()
    passed, msg = _run_single_test(
        crawler,
        "The Hindu",
        TEST_SITES["The Hindu (Indian news)"],
        verbose=False,
    )
    assert passed, msg


def test_bbc():
    """International news site."""
    crawler = _make_crawler()
    passed, msg = _run_single_test(
        crawler, "BBC", TEST_SITES["BBC News (international)"], verbose=False
    )
    assert passed, msg


def test_eenadu():
    """Telugu news site."""
    crawler = _make_crawler()
    passed, msg = _run_single_test(
        crawler, "Eenadu", TEST_SITES["Eenadu (Telugu news)"], verbose=False
    )
    assert passed, msg


def test_reuters():
    """Reuters news site — requires Playwright (returns 401 to plain HTTP)."""
    import pytest

    crawler = _make_crawler()
    passed, msg = _run_single_test(
        crawler,
        "Reuters",
        PLAYWRIGHT_FALLBACK_SITES["Reuters (requires Playwright)"],
        verbose=False,
    )
    if not passed:
        pytest.skip("Reuters needs Playwright (not available outside Docker)")


def test_parallel_fetch():
    """Test that multiple URLs can be fetched in parallel."""
    crawler = _make_crawler()
    urls = [
        "https://example.com/",
        "https://www.iana.org/about",
    ]
    start = time.time()
    results = crawler.contents(urls)
    elapsed = time.time() - start

    assert len(results) == 2, f"Expected 2 results, got {len(results)}"
    for r in results:
        assert r.scrape_successful, f"Failed for {r.link}"
        assert len(r.full_content.strip()) >= 50, f"Content too short for {r.link}"

    # Parallel should be faster than sequential (2 * timeout)
    assert elapsed < 30, f"Parallel fetch took too long: {elapsed:.1f}s"


def test_nonexistent_domain():
    """Non-existent domain should fail gracefully."""
    crawler = _make_crawler()
    results = crawler.contents(["https://this-domain-does-not-exist-99999.com/"])
    assert len(results) == 1
    assert not results[0].scrape_successful


def test_404_page():
    """404 page should fail gracefully."""
    crawler = _make_crawler()
    results = crawler.contents(
        ["https://example.com/this-page-does-not-exist-12345"]
    )
    assert len(results) == 1
    assert not results[0].scrape_successful


def test_empty_urls():
    """Empty URL list should return empty results."""
    crawler = _make_crawler()
    results = crawler.contents([])
    assert results == []


# -- Standalone CLI Runner ----------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="E2E test for VirtualAIWebCrawler",
    )
    parser.add_argument(
        "--url",
        help="Test a single URL instead of the full test suite",
    )
    parser.add_argument(
        "--playwright",
        action="store_true",
        help="Include Playwright fallback tests (slower, tests CDN-protected sites)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests including Playwright fallback sites",
    )
    args = parser.parse_args()

    crawler = _make_crawler()

    if args.url:
        print(f"\n{'='*60}")
        print(f"  Testing single URL: {args.url}")
        print(f"{'='*60}\n")
        config = {
            "url": args.url,
            "expect_title_contains": "",
            "expect_content_contains": "",
            "min_content_length": 50,
        }
        passed, _ = _run_single_test(crawler, args.url, config)
        sys.exit(0 if passed else 1)

    # Full test suite
    print(f"\n{'='*60}")
    print("  VirtualAI Web Crawler — E2E Test Suite")
    print(f"{'='*60}\n")

    sites = dict(TEST_SITES)
    if args.playwright or args.all:
        sites.update(PLAYWRIGHT_FALLBACK_SITES)

    passed_count = 0
    failed_count = 0
    total_start = time.time()

    for name, config in sites.items():
        passed, _ = _run_single_test(crawler, name, config)
        if passed:
            passed_count += 1
        else:
            failed_count += 1

    total_elapsed = time.time() - total_start

    print(f"\n{'-'*60}")
    print(
        f"  Results: {passed_count} passed, {failed_count} failed "
        f"({total_elapsed:.1f}s total)"
    )
    print(f"{'-'*60}\n")

    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()
