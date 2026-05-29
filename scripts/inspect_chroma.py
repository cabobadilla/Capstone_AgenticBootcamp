"""
Inspect what's in a ChromaDB collection — useful for validating ingestion quality.

Usage:
    python scripts/inspect_chroma.py --pack cca-f
    python scripts/inspect_chroma.py --pack cca-f --domain D1 --sample 10
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_tutor.ingestion.index import get_collection_stats, _get_collection


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a ChromaDB collection")
    parser.add_argument("--pack", required=True, help="Pack ID (e.g., cca-f)")
    parser.add_argument("--domain", default=None, help="Filter to a specific domain (e.g., D1)")
    parser.add_argument("--sample", type=int, default=5, help="Number of sample chunks to show")
    args = parser.parse_args()

    stats = get_collection_stats(args.pack)
    print(f"\n=== Collection: pack_{args.pack} ===")
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Domain distribution: {stats['domains']}")

    if stats["total_chunks"] == 0:
        print("No chunks — run ingestion first.")
        return

    # Show sample chunks
    collection = _get_collection(args.pack)
    where_filter = {"domain": args.domain} if args.domain else None

    results = collection.get(
        limit=args.sample,
        where=where_filter,
        include=["documents", "metadatas"],
    )

    print(f"\n=== Sample {args.sample} chunks{' (domain=' + args.domain + ')' if args.domain else ''} ===\n")
    for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"]), 1):
        print(f"--- Chunk {i} ---")
        print(f"  Source: {meta.get('source_url', 'n/a')}")
        print(f"  Section: {meta.get('section_path', 'n/a')}")
        print(f"  Domain: {meta.get('domain', 'n/a')} | Tier: {meta.get('tier', 'n/a')}")
        print(f"  Content ({len(doc)} chars): {doc[:200]}...")
        print()


if __name__ == "__main__":
    main()
