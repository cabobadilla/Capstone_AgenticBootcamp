"""
Ingestion orchestrator — fetch → extract → chunk → embed → index a Certification Pack.

Usage:
    python scripts/ingest_pack.py --pack cca-f              # all domains
    python scripts/ingest_pack.py --pack cca-f --domain D1  # one domain (MVP scope)

After ingestion, a manifest JSON is written to data/manifests/<pack>_<domains>_<version>.json
listing all URLs, chunk counts, and per-domain stats.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

# Add project root to path so scripts/ can import ai_tutor
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_tutor.config import settings
from ai_tutor.ingestion.chunk import chunk_all
from ai_tutor.ingestion.embed import embed_chunks
from ai_tutor.ingestion.extract import extract_all
from ai_tutor.ingestion.fetch import fetch_all
from ai_tutor.ingestion.index import get_collection_stats, index_chunks
from ai_tutor.packs.loader import load_corpus_urls, load_pack


def run_ingestion(pack_id: str, domain_filter: list[str] | None = None) -> dict:
    """
    Run the full ingestion pipeline for a pack (optionally filtered to specific domains).
    Returns a manifest dict summarizing what was ingested.
    """
    logger.info(f"=== Starting ingestion: pack={pack_id}, domains={domain_filter or 'all'} ===")

    # Ensure data directories exist
    settings.ensure_dirs()
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    Path("data/manifests").mkdir(parents=True, exist_ok=True)

    # ── Step 1: Load Pack metadata ────────────────────────────────────────────
    logger.info("Step 1/5: Loading Pack descriptor")
    pack = load_pack(pack_id)
    logger.info(f"Pack loaded: {pack.name} ({len(pack.domains)} domains, {len(pack.concepts)} concepts)")

    # ── Step 2: Load corpus URL list ─────────────────────────────────────────
    logger.info("Step 2/5: Loading corpus URL list")
    url_entries = load_corpus_urls(pack_id, domains=domain_filter)

    # Tag each entry with pack_id (needed for ChromaDB metadata)
    for entry in url_entries:
        entry["pack_id"] = pack_id

    if not url_entries:
        logger.error("No URLs found for the specified domains. Check corpus_urls.yaml.")
        return {}

    logger.info(f"Found {len(url_entries)} URLs to ingest")

    # ── Step 3: Fetch ─────────────────────────────────────────────────────────
    logger.info("Step 3/5: Fetching URLs (1s delay between requests)")
    fetched = fetch_all(url_entries)

    # ── Step 4: Extract ───────────────────────────────────────────────────────
    logger.info("Step 4/5: Extracting clean Markdown from fetched content")
    extracted = extract_all(fetched)

    # ── Step 5: Chunk (A2 strategy) ───────────────────────────────────────────
    logger.info("Step 5a/5: Chunking (markdown header-aware → size-bound)")
    chunks = chunk_all(extracted, corpus_version=pack.corpus_version)

    if not chunks:
        logger.error("No chunks produced — check if URLs returned content")
        return {}

    # ── Step 5b: Embed ────────────────────────────────────────────────────────
    logger.info(f"Step 5b/5: Embedding {len(chunks)} chunks with OpenAI text-embedding-3-small")
    embedded = embed_chunks(chunks)

    # ── Step 5c: Index ────────────────────────────────────────────────────────
    logger.info(f"Step 5c/5: Indexing into ChromaDB collection pack_{pack_id}")
    indexed_count = index_chunks(embedded, pack_id=pack_id)

    # ── Write manifest ────────────────────────────────────────────────────────
    stats = get_collection_stats(pack_id)
    domains_label = "_".join(sorted(domain_filter)) if domain_filter else "all"
    manifest_path = Path(f"data/manifests/{pack_id}_{domains_label}_{pack.corpus_version}.json")

    manifest = {
        "pack_id": pack_id,
        "pack_name": pack.name,
        "corpus_version": pack.corpus_version,
        "domains_ingested": domain_filter or [d.id for d in pack.domains],
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "url_count": len(url_entries),
        "fetch_ok": sum(1 for f in fetched if f.get("fetch_ok")),
        "fetch_failed": sum(1 for f in fetched if not f.get("fetch_ok")),
        "chunks_produced": len(chunks),
        "chunks_indexed": indexed_count,
        "collection_stats": stats,
        "urls": [
            {
                "url": e["url"],
                "title": e.get("title", ""),
                "domain": e.get("domain", ""),
                "tier": e.get("tier", 1),
                "fetch_ok": e.get("fetch_ok", False),
            }
            for e in fetched
        ],
    }

    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info(f"Manifest written to {manifest_path}")
    logger.info(f"=== Ingestion complete: {indexed_count} chunks indexed ===")

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a Certification Pack into ChromaDB")
    parser.add_argument("--pack", required=True, help="Pack ID (e.g., cca-f)")
    parser.add_argument("--domain", default=None, help="Single domain to ingest (e.g., D1). Omit for all domains.")
    args = parser.parse_args()

    domain_filter = [args.domain] if args.domain else None
    manifest = run_ingestion(args.pack, domain_filter=domain_filter)

    if manifest:
        print(f"\n✓ Ingested {manifest['chunks_indexed']} chunks into pack_{args.pack}")
        print(f"  Domains: {manifest['domains_ingested']}")
        print(f"  URLs: {manifest['fetch_ok']}/{manifest['url_count']} successful")
        print(f"  Collection stats: {manifest['collection_stats']['domains']}")
    else:
        print("✗ Ingestion failed — check logs above")
        sys.exit(1)


if __name__ == "__main__":
    main()
