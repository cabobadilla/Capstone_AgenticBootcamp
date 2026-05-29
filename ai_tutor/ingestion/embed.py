"""
Embed chunks using OpenAI text-embedding-3-small.

Closed decision (spec v2 §13): OpenAI text-embedding-3-small is the primary embeddings
provider. Voyage AI voyage-3 was the spec's preferred option but OpenAI was selected
because the API key was already available.

Batching: OpenAI allows up to 2048 texts per request; we use 50 as a conservative
batch size to stay well within rate limits and make progress logs readable.

Retry: tenacity with exponential backoff handles transient API errors (rate limits,
5xx responses) without crashing the ingestion run.
"""

import time
from typing import Callable

from loguru import logger
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from ai_tutor.config import settings

_BATCH_SIZE = 50           # chunks per OpenAI embeddings API call
_EMBEDDING_DIM = 1536      # text-embedding-3-small output dimension

_client = OpenAI(api_key=settings.openai_api_key)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Call OpenAI embeddings API for a batch of texts.
    tenacity retries on any exception with exponential backoff (2s → 4s → 8s → fail).
    """
    response = _client.embeddings.create(
        model=settings.embedding_model,   # "text-embedding-3-small"
        input=texts,
    )
    # API returns embeddings in the same order as input texts
    return [item.embedding for item in response.data]


def embed_chunks(chunks: list[dict], progress_callback: Callable[[int, int], None] | None = None) -> list[dict]:
    """
    Add embeddings to each chunk dict.

    Returns the same list with `embedding: list[float]` added to each chunk.
    Chunks that fail to embed get `embedding: None` and are skipped at index time.
    """
    total = len(chunks)
    embedded: list[dict] = []

    for batch_start in range(0, total, _BATCH_SIZE):
        batch = chunks[batch_start : batch_start + _BATCH_SIZE]
        texts = [c["content"] for c in batch]

        try:
            vectors = _embed_batch(texts)
            for chunk, vector in zip(batch, vectors):
                embedded.append({**chunk, "embedding": vector})
        except Exception as e:
            logger.error(f"Embedding batch {batch_start}-{batch_start + len(batch)} failed: {e}")
            # Mark these chunks as failed — they will be skipped in index.py
            for chunk in batch:
                embedded.append({**chunk, "embedding": None})

        done = min(batch_start + _BATCH_SIZE, total)
        logger.info(f"Embedded {done}/{total} chunks")

        if progress_callback:
            progress_callback(done, total)

        # Brief pause between batches to be a polite API citizen
        if batch_start + _BATCH_SIZE < total:
            time.sleep(0.2)

    successful = sum(1 for c in embedded if c.get("embedding") is not None)
    logger.info(f"Embedding complete: {successful}/{total} chunks embedded successfully")
    return embedded
