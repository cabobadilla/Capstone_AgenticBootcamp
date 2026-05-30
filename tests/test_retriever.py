"""Retriever tests — validates pack-scoped, domain-filtered retrieval."""

import pytest

from ai_tutor.config import settings
from ai_tutor.models import Chunk
from ai_tutor.rag.retriever import retrieve, retrieve_for_concept

NEEDS_CHROMA = pytest.mark.skipif(
    not (settings.chroma_persist_dir / "chroma.sqlite3").exists(),
    reason="ChromaDB not initialised — run ingestion first",
)


@NEEDS_CHROMA
def test_retrieve_returns_chunks():
    chunks = retrieve("cca-f", "tool use agentic loop", k=3)
    assert len(chunks) >= 1
    for c in chunks:
        assert isinstance(c, Chunk)
        assert c.source_url.startswith("http")
        assert len(c.content) > 50
        assert 0.0 <= c.score <= 1.0


@NEEDS_CHROMA
def test_retrieve_domain_filter():
    """Domain filter must only return chunks tagged with that domain."""
    chunks = retrieve("cca-f", "orchestration pattern", domain="D1", k=5)
    for c in chunks:
        assert c.domain == "D1", f"Expected D1, got {c.domain}"


@NEEDS_CHROMA
def test_retrieve_for_concept_returns_chunks():
    chunks = retrieve_for_concept("cca-f", "agentic_loop_basics", domain="D1")
    assert len(chunks) >= 1


@NEEDS_CHROMA
def test_retrieve_all_domains():
    """All 5 domains must be reachable via retrieval."""
    for domain in ["D1", "D2", "D3", "D4", "D5"]:
        chunks = retrieve("cca-f", "concept definition", domain=domain, k=3)
        assert len(chunks) >= 1, f"No chunks found for domain {domain}"
