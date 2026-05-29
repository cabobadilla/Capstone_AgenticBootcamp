"""
Chunk extracted Markdown text into RAG-ready pieces.

Strategy A2 (closed decision, spec v2 §10):
  Step 1 — MarkdownHeaderTextSplitter: split on #/##/### headers, preserving
            the header breadcrumb path in metadata as `section_path`.
  Step 2 — RecursiveCharacterTextSplitter: size-bound each section to ≤1000 tokens
            (approx 4 chars/token → 4000 chars) with 100-token overlap.

Why A2 over A1 (fixed-size): Anthropic docs and MCP spec use consistent headers.
Splitting there keeps each chunk semantically coherent — one concept per chunk —
which directly improves retrieval precision for scenario-based D1 questions.
"""

from datetime import datetime, timezone

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from loguru import logger

# Headers to split on — keep breadcrumb as (header_text, metadata_key) tuples
_HEADER_SPLITTER = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
    ],
    strip_headers=False,  # keep the header in the chunk text so context is preserved
)

# After header-splitting, size-bound to ~1000 tokens (4000 chars) with 100-token overlap
# RecursiveCharacterTextSplitter respects paragraph → sentence → word → char boundaries
_SIZE_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=4000,       # ~1000 tokens at 4 chars/token
    chunk_overlap=400,     # ~100-token overlap
    length_function=len,
    separators=["\n\n", "\n", " ", ""],
)


def _build_section_path(metadata: dict) -> str:
    """Build a human-readable breadcrumb from header metadata. E.g. 'h1 > h2 > h3'."""
    parts = []
    for key in ["h1", "h2", "h3"]:
        val = metadata.get(key, "").strip()
        if val:
            parts.append(val)
    return " > ".join(parts) if parts else ""


def chunk_document(entry: dict, corpus_version: str = "v1") -> list[dict]:
    """
    Chunk a single extracted document into RAG-ready pieces.

    Returns a list of chunk dicts with all ChromaDB metadata fields (spec v2 §9.4).
    Returns empty list if the document has no extracted text.
    """
    text = entry.get("extracted_text", "").strip()
    if not text:
        return []

    url = entry.get("url", "")
    title = entry.get("title", "")
    domain = entry.get("domain", "")
    domain_weight = entry.get("domain_weight", 0.0)
    tier = entry.get("tier", 1)

    # Step 1: split on markdown headers
    header_docs = _HEADER_SPLITTER.split_text(text)

    chunks = []
    for doc in header_docs:
        section_path = _build_section_path(doc.metadata)

        # Step 2: size-bound each section
        sub_texts = _SIZE_SPLITTER.split_text(doc.page_content)

        for sub_text in sub_texts:
            sub_text = sub_text.strip()
            if len(sub_text) < 100:
                # Skip tiny fragments (typically just a header with no body)
                continue

            chunks.append({
                # Content
                "content": sub_text,
                # Provenance — all metadata required for citation validation
                "source_url": url,
                "source_title": title,
                "section_path": section_path,
                # Pack taxonomy
                "pack_id": entry.get("pack_id", ""),
                "domain": domain,
                "domain_weight": domain_weight,
                "tier": tier,
                # Content classification (default "concept"; can be enriched later)
                "content_type": "concept",
                "concept_tags": [],
                # Versioning
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "corpus_version": corpus_version,
            })

    return chunks


def chunk_all(extracted_entries: list[dict], corpus_version: str = "v1") -> list[dict]:
    """Chunk all extracted documents."""
    all_chunks: list[dict] = []

    for entry in extracted_entries:
        chunks = chunk_document(entry, corpus_version=corpus_version)
        all_chunks.extend(chunks)
        if chunks:
            logger.debug(f"  {entry['url']}: {len(chunks)} chunks")

    logger.info(f"Chunking complete: {len(all_chunks)} total chunks from {len(extracted_entries)} documents")
    return all_chunks
