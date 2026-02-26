# News Crawling Enhancement Plan

## Current System Summary

| Component | File | What It Does |
|-----------|------|-------------|
| Web Connector | `backend/onyx/connectors/web/connector.py` | Playwright browser crawling. 4 modes: recursive, single, sitemap, upload. Bot evasion, retry, dedup. |
| HTML Extraction | `backend/onyx/file_processing/html_utils.py` | BeautifulSoup cleanup + optional trafilatura (`PARSE_WITH_TRAFILATURA=true`) |
| Sitemap Parser | `backend/onyx/utils/sitemap.py` | Extracts `<loc>` URLs from standard sitemaps. Does NOT parse `news:news` metadata. |
| Frontend Config | `web/src/lib/connectors/connectors.tsx` (lines 149-183) | Web connector UI: base_url, scrape method, scroll checkbox |

### Using It for News Today (No Code Changes)

- **Sitemap mode**: set `base_url` to news sitemap URL, `web_connector_type: "sitemap"`
- **Enable trafilatura**: set `PARSE_WITH_TRAFILATURA=true` for clean article extraction
- **Shorten update frequency**: 1-4 hours instead of default 24h

---

## Research: All Major News Sites Use Google News Sitemaps

```xml
<urlset xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <url>
    <loc>https://example.com/article/123</loc>
    <lastmod>2026-02-25T08:41:52+05:30</lastmod>
    <news:news>
      <news:publication>
        <news:name>The Hindu</news:name>
        <news:language>en</news:language>
      </news:publication>
      <news:publication_date>2026-02-25T08:41:52+05:30</news:publication_date>
      <news:title>Article Title Here</news:title>
      <news:keywords>keyword1, keyword2</news:keywords>
    </news:news>
  </url>
</urlset>
```

| Site | News Sitemap URL | Language | Has Keywords |
|------|-----------------|----------|-------------|
| The Hindu | `/sitemap/googlenews/all/all.xml` | en | Yes |
| BBC | `/sitemaps/https-index-com-news.xml` (index) | en | No |
| Reuters | `/arc/outboundfeeds/news-sitemap/?outputType=xml` | en | Yes |
| Eenadu | `/sitemap-news.xml` | te (Telugu) | Yes |
| TOI | `/sitemap/today` | en | Yes |
| NDTV | Blocked by CDN (use RSS feeds via feedburner) | en | N/A |

---

## What's Missing (The Gap)

Current `sitemap.py` only extracts `<loc>` URLs and throws away all `news:news` metadata. This means:

- No publish date on documents (can't sort by recency)
- No article title from sitemap (must fetch full page for title)
- No keywords (missed metadata for search)
- No incremental crawling (re-fetches everything every run)

---

## Implementation Steps

### Step 1: Enhance Sitemap Parser for News Metadata

**File:** `backend/onyx/utils/sitemap.py`

- Add `SitemapEntry` dataclass: `url`, `lastmod`, `title`, `publication_date`, `keywords`, `language`, `image_url`
- Parse `news:` namespace tags (`news:publication_date`, `news:title`, `news:keywords`)
- Parse `image:` namespace for thumbnail URLs
- Add new function `list_pages_with_metadata()` returning `list[SitemapEntry]`
- Keep `list_pages_for_site()` returning `list[str]` for backward compatibility

### Step 2: Wire News Metadata into Web Connector

**File:** `backend/onyx/connectors/web/connector.py`

- In sitemap mode, call `list_pages_with_metadata()` instead of `extract_urls_from_sitemap()`
- Store `SitemapEntry` metadata alongside URLs in `ScrapeSessionContext`
- Populate Document fields:
  - `doc_updated_at` from `news:publication_date`
  - `metadata` dict with `title`, `keywords`, `language`, `image_url`
  - `semantic_identifier` from `news:title` as fallback

### Step 3: Extract Article Metadata from HTML

**File:** `backend/onyx/file_processing/html_utils.py`

Add `extract_article_metadata(soup) -> dict` that parses:

- **JSON-LD** (`<script type="application/ld+json">`) — `author`, `datePublished`, `headline`, `description`
- **Open Graph** (`<meta property="og:*">`) — `og:title`, `og:description`, `article:published_time`, `article:author`
- **Standard meta** — `<meta name="author">`, `<meta name="keywords">`

Merge into Document metadata. Priority: JSON-LD > Open Graph > meta tags.

### Step 4: Config Tuning (No Code)

```env
PARSE_WITH_TRAFILATURA=true
WEB_CONNECTOR_IGNORED_CLASSES=sidebar,footer,advertisement,ad-container,social-share,related-articles
WEB_CONNECTOR_IGNORED_ELEMENTS=nav,footer,meta,script,style,symbol,aside,iframe
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `backend/onyx/utils/sitemap.py` | Add `SitemapEntry`, `list_pages_with_metadata()`, parse news namespace |
| `backend/onyx/connectors/web/connector.py` | Use metadata-aware sitemap parser, populate Document fields |
| `backend/onyx/file_processing/html_utils.py` | Add `extract_article_metadata()` for JSON-LD / OG / meta |

## Verification

1. Parse sample XML from The Hindu, BBC, Reuters, Eenadu, TOI — verify `SitemapEntry` fields
2. Run connector in sitemap mode against `https://www.thehindu.com/sitemap/googlenews/all/all.xml`
3. Verify documents have `doc_updated_at`, keywords, clean article text
4. Verify `list_pages_for_site()` still works for non-news sitemaps
5. Run `pytest backend/tests/daily/connectors/web/test_web_connector.py`
