"""
Fetch raw content from URLs in the corpus.

Handles three source types:
  1. Regular HTML pages (Anthropic docs, MCP spec) — returned as raw HTML string.
  2. GitHub blob URLs — rewritten to raw.githubusercontent.com to get plain text.
  3. GitHub .ipynb notebook URLs — fetched as JSON for nbformat processing.

Respectful crawling: 1-second delay between requests (spec v2 §9.4 Step 2).
"""

import time
from urllib.parse import urlparse

import requests
from loguru import logger

# Respectful crawl delay between requests (avoids rate-limiting on docs.anthropic.com)
_CRAWL_DELAY_S = 1.0

# Timeout per request — 30s is generous but docs pages can be slow
_REQUEST_TIMEOUT_S = 30

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "ai-tutor-ingestion/1.0 (educational capstone project)"})


def _github_blob_to_raw(url: str) -> str:
    """
    Convert a GitHub blob URL to raw.githubusercontent.com equivalent.
    e.g. https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/README.md
      → https://raw.githubusercontent.com/anthropics/anthropic-cookbook/main/patterns/agents/README.md
    """
    # Replace domain and strip /blob/ path segment
    raw = url.replace("github.com", "raw.githubusercontent.com")
    raw = raw.replace("/blob/", "/")
    return raw


def fetch_url(url: str, delay: bool = True) -> tuple[str, str]:
    """
    Fetch a single URL and return (content, content_type).

    content_type is one of: "html", "text", "notebook"
    Raises requests.HTTPError on non-2xx responses.
    """
    if delay:
        time.sleep(_CRAWL_DELAY_S)

    parsed = urlparse(url)
    is_github = parsed.netloc in ("github.com", "raw.githubusercontent.com")
    is_notebook = url.endswith(".ipynb")

    # Rewrite GitHub blob URLs to raw before fetching
    fetch_url_target = _github_blob_to_raw(url) if "github.com" in url and "/blob/" in url else url

    logger.debug(f"Fetching: {fetch_url_target}")
    response = _SESSION.get(fetch_url_target, timeout=_REQUEST_TIMEOUT_S)
    response.raise_for_status()

    if is_notebook:
        # Return raw JSON text; extract.py will parse it with nbformat
        return response.text, "notebook"
    elif is_github or "raw.githubusercontent.com" in fetch_url_target:
        # Already plain text (markdown, plain source)
        return response.text, "text"
    else:
        return response.text, "html"


def fetch_all(url_entries: list[dict]) -> list[dict]:
    """
    Fetch all URLs in the corpus entries list.

    Returns list of dicts with original entry fields plus:
      - raw_content: str
      - content_type: "html" | "text" | "notebook"
      - fetch_ok: bool
      - fetch_error: str | None
    """
    results = []
    total = len(url_entries)

    for i, entry in enumerate(url_entries, 1):
        url = entry["url"]
        logger.info(f"[{i}/{total}] Fetching {url}")

        try:
            # First request doesn't need extra delay (already starts from 0)
            content, content_type = fetch_url(url, delay=(i > 1))
            results.append({**entry, "raw_content": content, "content_type": content_type, "fetch_ok": True, "fetch_error": None})
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            results.append({**entry, "raw_content": "", "content_type": "html", "fetch_ok": False, "fetch_error": str(e)})

    successful = sum(1 for r in results if r["fetch_ok"])
    logger.info(f"Fetch complete: {successful}/{total} URLs successful")
    return results
