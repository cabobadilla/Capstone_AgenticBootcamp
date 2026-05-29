"""
RAG retriever — queries the active Pack's ChromaDB collection.

Every retrieval is scoped to a specific pack_id (and optionally a domain) so
agents never accidentally read from a different Pack's corpus. This is the
enforcement point for the platform's Pack-isolation guarantee (spec v2 §2).

Retrieval uses cosine similarity (set at collection-creation time in index.py).
Top-k defaults to settings.retrieval_top_k (5), which keeps context tight and
per-session cost under the $0.50 NF-06 ceiling.
"""

import chromadb
from loguru import logger

from ai_tutor.config import settings
from ai_tutor.ingestion.embed import _client as openai_client
from ai_tutor.models import Chunk


def _embed_query(query: str) -> list[float]:
    """Embed a retrieval query using the same model used at ingest time."""
    response = openai_client.embeddings.create(
        model=settings.embedding_model,
        input=[query],
    )
    return response.data[0].embedding


def _get_collection(pack_id: str) -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(settings.chroma_persist_dir))
    return client.get_collection(name=f"pack_{pack_id}")


def retrieve(
    pack_id: str,
    query: str,
    domain: str | None = None,
    k: int | None = None,
) -> list[Chunk]:
    """
    Retrieve the top-k most relevant chunks for a query within a Pack.

    Args:
        pack_id:  active Pack ID (e.g., "cca-f") — used to scope the collection.
        query:    free-text query or concept name used as the similarity search input.
        domain:   optional domain filter (e.g., "D1") — restricts results to one exam domain.
        k:        number of chunks to return (defaults to settings.retrieval_top_k = 5).

    Returns list of Chunk objects sorted by relevance (highest first).
    """
    k = k or settings.retrieval_top_k

    try:
        collection = _get_collection(pack_id)
    except Exception as e:
        logger.error(f"Collection pack_{pack_id} not found — run ingestion first. Error: {e}")
        return []

    # Embed the query with the same model used at ingest time
    query_embedding = _embed_query(query)

    # Build optional domain filter — ChromaDB `where` clause
    where_filter = {"domain": domain} if domain else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(k, collection.count()),  # guard against k > collection size
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[Chunk] = []
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    for doc, meta, dist in zip(docs, metas, distances):
        # ChromaDB cosine distance → similarity score (1 - distance)
        score = 1.0 - dist

        # concept_tags stored as comma-separated string in ChromaDB metadata
        concept_tags = [t for t in meta.get("concept_tags", "").split(",") if t]

        chunks.append(Chunk(
            content=doc,
            source_url=meta.get("source_url", ""),
            source_title=meta.get("source_title", ""),
            tier=int(meta.get("tier", 1)),
            domain=meta.get("domain", ""),
            domain_weight=float(meta.get("domain_weight", 0.0)),
            section_path=meta.get("section_path", ""),
            concept_tags=concept_tags,
            content_type=meta.get("content_type", "concept"),
            score=score,
        ))

    logger.debug(f"Retrieved {len(chunks)} chunks for query='{query[:50]}' domain={domain} pack={pack_id}")
    return chunks


def retrieve_for_concept(pack_id: str, concept: str, domain: str, difficulty: str = "conceptual") -> list[Chunk]:
    """
    Convenience wrapper that builds a retrieval query tuned for exam-question generation.

    The query is enriched with difficulty context so the embedding points toward
    the right kind of content (conceptual definitions vs scenario examples).
    """
    if difficulty == "scenario":
        query = f"{concept} production scenario example anti-pattern architecture decision"
    else:
        query = f"{concept} definition mechanism how it works"

    return retrieve(pack_id=pack_id, query=query, domain=domain)
