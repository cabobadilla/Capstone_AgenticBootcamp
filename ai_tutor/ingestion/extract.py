"""
Extract clean Markdown text from raw fetched content.

Three extraction paths:
  1. HTML → trafilatura strips navigation/headers/footers, returns Markdown.
  2. Plain text (GitHub raw markdown) → passed through as-is.
  3. Jupyter notebooks (.ipynb) → nbformat parses cells; markdown + code concatenated.

Why trafilatura: it's specifically designed for article/documentation extraction,
producing cleaner Markdown than BeautifulSoup or html2text for docs pages.
"""

import json

import nbformat
import trafilatura
from loguru import logger


def extract_html(raw_html: str, url: str = "") -> str:
    """
    Convert HTML to clean Markdown using trafilatura.

    include_formatting=True preserves bold/code/links as Markdown.
    output_format="markdown" vs "text" — markdown keeps code blocks.
    """
    result = trafilatura.extract(
        raw_html,
        url=url,
        include_formatting=True,
        include_links=False,      # links add noise; we have source_url in metadata
        include_images=False,
        output_format="markdown",
        favor_recall=True,        # prefer getting more content over precision (docs pages are signal-dense)
    )

    if not result:
        logger.warning(f"trafilatura extracted nothing from {url} — falling back to raw text")
        # Last resort: strip all tags manually (rare case)
        import re
        result = re.sub(r"<[^>]+>", " ", raw_html)
        result = " ".join(result.split())

    return result or ""


def extract_notebook(raw_json: str) -> str:
    """
    Extract text from a Jupyter notebook JSON.
    Concatenates markdown cells + code cells (fenced with ```python).
    """
    try:
        nb = nbformat.reads(raw_json, as_version=4)
    except Exception as e:
        logger.warning(f"nbformat failed to parse notebook: {e}")
        return ""

    parts = []
    for cell in nb.cells:
        source = cell.source.strip()
        if not source:
            continue

        if cell.cell_type == "markdown":
            parts.append(source)
        elif cell.cell_type == "code":
            # Fence code cells so the chunker preserves them as code blocks
            parts.append(f"```python\n{source}\n```")

    return "\n\n".join(parts)


def extract(entry: dict) -> dict:
    """
    Extract clean Markdown from a fetched URL entry.
    Returns the entry dict with `extracted_text` added.
    """
    if not entry.get("fetch_ok"):
        return {**entry, "extracted_text": ""}

    content_type = entry["content_type"]
    raw = entry["raw_content"]
    url = entry.get("url", "")

    if content_type == "notebook":
        text = extract_notebook(raw)
    elif content_type == "text":
        # Already plain text/markdown — use as-is
        text = raw
    else:
        # HTML — use trafilatura
        text = extract_html(raw, url=url)

    logger.debug(f"Extracted {len(text)} chars from {url}")
    return {**entry, "extracted_text": text}


def extract_all(fetched_entries: list[dict]) -> list[dict]:
    """Extract text from all fetched entries."""
    results = []
    for entry in fetched_entries:
        results.append(extract(entry))

    extracted_ok = sum(1 for r in results if r.get("extracted_text"))
    logger.info(f"Extraction complete: {extracted_ok}/{len(results)} entries have content")
    return results
