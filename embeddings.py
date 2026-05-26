"""Helpers for MongoDB Automated Embedding (autoEmbed) indexes."""

from __future__ import annotations

import time
from typing import Any

import requests
from pymongo.collection import Collection
from pymongo.mongo_client import MongoClient

from config import EMBEDDING_MODEL, MV_DATABASE, VOYAGE_API_KEY, VOYAGE_EMBEDDINGS_URL


def create_embeddings_via_api(
    texts: str | list[str],
    *,
    model: str | None = None,
    input_type: str | None = None,
) -> list[list[float]]:
    """
    Call the MongoDB/Voyage embedding REST API directly.

    Atlas model API keys route to https://ai.mongodb.com/v1/embeddings.
    Used for validation or manual embedding workflows alongside autoEmbed indexes.
    """
    if not VOYAGE_API_KEY:
        raise ValueError("VOYAGE_API_KEY is required to call the embeddings API")

    payload: dict[str, Any] = {
        "input": texts,
        "model": model or EMBEDDING_MODEL,
    }
    if input_type:
        payload["input_type"] = input_type

    response = requests.post(
        VOYAGE_EMBEDDINGS_URL,
        headers={
            "Authorization": f"Bearer {VOYAGE_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()["data"]
    return [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]


def get_mv_collection(
    client: MongoClient,
    source_db: str,
    source_collection: str,
    index_name: str,
):
    """Resolve the internal generated-embeddings collection for an auto-embed index."""
    src = client[source_db][source_collection]
    indexes = list(src.aggregate([{"$listSearchIndexes": {"name": index_name}}]))
    if not indexes:
        raise LookupError(
            f"No search index named {index_name!r} on {source_db}.{source_collection}"
        )

    index_id = indexes[0]["id"]
    mv_db = client[MV_DATABASE]
    matches = [name for name in mv_db.list_collection_names() if name.startswith(index_id)]
    if not matches:
        raise LookupError(
            f"No generated-embeddings collection for index {index_id!r} "
            "(index may still be building or initial sync not started)"
        )
    if len(matches) > 1:
        matches.sort(reverse=True)
    return mv_db[matches[0]]


def has_embedding(
    client: MongoClient,
    source_db: str,
    source_collection: str,
    index_name: str,
    embed_path: str,
    source_id: Any,
) -> bool:
    """Return True if an auto-generated embedding exists for the source document."""
    try:
        mv = get_mv_collection(client, source_db, source_collection, index_name)
    except LookupError:
        return False

    doc = mv.find_one(
        {"_id": source_id},
        {"_id": 1, f"_autoEmbed.{embed_path}": 1},
    )
    if not doc:
        return False
    auto_embed = doc.get("_autoEmbed", {})
    embedding = auto_embed.get(embed_path)
    return embedding is not None and len(embedding) > 0


def wait_for_embedding(
    client: MongoClient,
    source_db: str,
    source_collection: str,
    index_name: str,
    embed_path: str,
    source_id: Any,
    *,
    timeout_seconds: int = 120,
    poll_interval_seconds: float = 2.0,
) -> bool:
    """Poll until an embedding exists or timeout is reached."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if has_embedding(
            client, source_db, source_collection, index_name, embed_path, source_id
        ):
            return True
        time.sleep(poll_interval_seconds)
    return False


def wait_for_search_index(
    collection: Collection,
    index_name: str,
    *,
    timeout_seconds: int = 600,
    poll_interval_seconds: float = 5.0,
) -> dict:
    """Poll until a search index reaches READY status."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        indexes = list(collection.aggregate([{"$listSearchIndexes": {"name": index_name}}]))
        if indexes:
            index = indexes[0]
            status = index.get("status")
            if status == "READY":
                return index
            if status in {"FAILED", "DELETING"}:
                raise RuntimeError(f"Search index {index_name!r} entered status {status!r}")
            print(f"  Index status: {status} (waiting...)")
        time.sleep(poll_interval_seconds)
    raise TimeoutError(f"Timed out waiting for search index {index_name!r} to become READY")


def vector_search(
    collection: Collection,
    *,
    index_name: str,
    embed_path: str,
    query_text: str,
    embedding_model: str,
    limit: int = 5,
) -> list[dict]:
    """Run an auto-embedding vector search query (query text, not pre-computed vectors)."""
    pipeline = [
        {
            "$vectorSearch": {
                "index": index_name,
                "path": embed_path,
                "query": query_text,
                "model": embedding_model,
                "numCandidates": max(limit * 10, 50),
                "limit": limit,
            }
        },
        {
            "$project": {
                "_id": 1,
                "score": {"$meta": "vectorSearchScore"},
                "simulation_id": 1,
                "name": 1,
                "description": 1,
                "data.simulation_id": 1,
                "data.name": 1,
                "data.description": 1,
            }
        },
    ]
    return list(collection.aggregate(pipeline))
