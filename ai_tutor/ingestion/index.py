"""
Index embedded chunks into ChromaDB.

Collection naming convention: `pack_<pack_id>` (e.g., `pack_cca-f`).
This isolates each Certification Pack's corpus and enables Pack-scoped retrieval.

ChromaDB is used in persistent-client mode so data survives across sessions.
The persist directory comes from settings.chroma_persist_dir (./data/chroma).

Metadata schema stored per chunk: all fields from spec v2 §9.4.
String-only metadata: ChromaDB metadata values must be str | int | float | bool — no lists.
concept_tags is stored as a comma-separated string and parsed back on retrieval.
"""

import uuid

import chromadb
from loguru import logger

from ai_tutor.config import settings


def _get_collection(pack_id: str) -> chromadb.Collection:
    """
    Get (or create) the ChromaDB collection for a pack.
    Collection name: pack_<pack_id> (e.g., pack_cca-f).
    """
    # Persistent client — data survives process restarts
    client = chromadb.PersistentClient(path=str(settings.chroma_persist_dir))

    collection_name = f"pack_{pack_id}"
    # get_or_create — safe to call multiple times; idempotent
    collection = client.get_or_create_collection(
        name=collection_name,
        # Cosine similarity is standard for semantic search; ChromaDB normalizes vectors
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def _prepare_metadata(chunk: dict) -> dict:
    """
    Flatten chunk metadata to ChromaDB-compatible types (str | int | float | bool only).
    Lists are serialized to comma-separated strings.
    """
    return {
        "source_url": chunk.get("source_url", ""),
        "source_title": chunk.get("source_title", ""),
        "section_path": chunk.get("section_path", ""),
        "pack_id": chunk.get("pack_id", ""),
        "domain": chunk.get("domain", ""),
        "domain_weight": float(chunk.get("domain_weight", 0.0)),
        "tier": int(chunk.get("tier", 1)),
        "content_type": chunk.get("content_type", "concept"),
        # Lists → comma-separated strings for ChromaDB compatibility
        "concept_tags": ",".join(chunk.get("concept_tags", [])),
        "ingested_at": chunk.get("ingested_at", ""),
        "corpus_version": chunk.get("corpus_version", "v1"),
    }


def index_chunks(chunks: list[dict], pack_id: str) -> int:
    """
    Index a list of embedded chunks into the pack's ChromaDB collection.

    Skips chunks with no embedding (failed embed step).
    Returns the number of chunks successfully indexed.
    """
    collection = _get_collection(pack_id)

    # Filter out chunks that failed embedding
    valid = [c for c in chunks if c.get("embedding") is not None]
    skipped = len(chunks) - len(valid)
    if skipped:
        logger.warning(f"Skipping {skipped} chunks with no embedding")

    if not valid:
        logger.error("No valid chunks to index")
        return 0

    # ChromaDB add() accepts lists — batch all at once for performance
    ids = [str(uuid.uuid4()) for _ in valid]
    documents = [c["content"] for c in valid]
    embeddings = [c["embedding"] for c in valid]
    metadatas = [_prepare_metadata(c) for c in valid]

    # ChromaDB upsert instead of add — idempotent if we re-run ingestion
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    count = collection.count()
    logger.info(f"Collection `pack_{pack_id}` now has {count} total chunks")
    return len(valid)


def get_collection_stats(pack_id: str) -> dict:
    """Return basic stats about the indexed collection (used by inspect_chroma.py)."""
    collection = _get_collection(pack_id)
    count = collection.count()

    # Sample a few entries to show domain distribution
    if count == 0:
        return {"pack_id": pack_id, "total_chunks": 0, "domains": {}}

    # Peek at up to 1000 entries to compute domain distribution
    sample = collection.get(limit=min(count, 1000), include=["metadatas"])
    domain_counts: dict[str, int] = {}
    for meta in sample["metadatas"]:
        d = meta.get("domain", "unknown")
        domain_counts[d] = domain_counts.get(d, 0) + 1

    return {
        "pack_id": pack_id,
        "collection_name": f"pack_{pack_id}",
        "total_chunks": count,
        "domains": domain_counts,
    }
